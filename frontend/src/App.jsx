// currently two active console.log, this is to confirm that websocket is receiving MessaveEvent object
// and passing it onto the onmessage event handler and its associated function.

import { useEffect, useState, useRef } from 'react';
import './App.css';
import axios from 'axios';
import useWebSocket, { readyState }  from 'react-use-websocket';


// App component is a functional component (that is, a component defined as a function instead of as
// an extension of the React.Component class). It is the main component of the application and is
// responsible for rendering the UI and handling user interactions. Mounting refers to the process
// of creating an instance of a component and inserting it into the DOM. Unmounting refers to the
// process of removing a component instance from the DOM. The App component is mounted when the
// application is loaded in the browser and unmounted when the application is closed or navigated
// away from.

function App() {
    // Defining state variables. 'useState' initalizes the layers state variable to 3.
    // Then, it provides a function 'setLayers' to update it. Similar initialization for the other state
    // variables.
    // const [layers, setLayers] = useState(3);
    // const [units, setUnits] = useState([32, 64, 128]);
    // const [epochs, setEpochs] = useState(50);
    // const [batchSize, setBatchSize] = useState(32);
    // const [optimizer, setOptimizer] = useState('adam');
    const [accuracy, setAccuracy] = useState(null);
    const [loss, setLoss] = useState(null);

    // Defining additional state variables to indicate whether model is currently training, as well
    // as if there is an error during training, as well as whether or not we're currently downloading
    // the cifar-10 dataset
    const [loading, setLoading] = useState(false);
    // const [downloading, setDownloading] = useState(false);
    const [error, setError] = useState(null);
    const [wsError, setWsError] = useState(null)

    // Defining one more state variable to store training progress data/outputs to show the user.
    const [trainingProgress, setTrainingProgress] = useState([]);


    // Defining local state variables for form inputs.

    const [inputLayers, setInputLayers] = useState(3);
    const [inputUnits, setInputUnits] = useState([32, 64, 128]);
    const [inputEpochs, setInputEpochs] = useState(50);
    const [inputBatchSize, setInputBatchSize] = useState(32);
    const [inputOptimizer, setInputOptimizer] = useState('adam');

    const wsRef = useRef(null);

    // Declaring a new websocket
    // ws:// is the websockot protocol
    // localhost: indicates the server is running on the same machine
    // rest of the URL is self-explanatory.

    // .onmessage is an event handler that listens for messages from the server via the websocket.
    // We're assigning to it a function to be called whenever .onmessage detects a message
    // from the server via the websocket.
    // The function takes an event object as a parameter, where event is a 'MessageEvent' object.
    // Basically, everytime a message is received, a 'MessageEvent' object is created and passed to
    // the 'onmessage' event handler as an 'event' parameter. This is then itself sent to the 
    // function we're defining here.
    useEffect(() => {
        console.log('use effect running again')
        const connect = () => {
            // the try block here is used to catch exceptions thrown while attempting to establish
            // a websocket connection, notably errors that occur synchronously, such as if the URL
            // is invalid or if the server is unreachable due to network issues. Errors arising within
            // the route itself are not caught by this try block. Instead, they are handBled by the onerror
            // event handler defined below. This is because as long as we don't encounter or invalid URLs,
            // we can expect the WebSocket object to have been created. If the websocket object has been
            // created, then the onerror event handler will be called if there are any issues with the
            // connection, such as the .accept() method not being called or facing some issue on the
            // server side.
            // 'ws://localhost:500/ws' - triggers onerror handler
            // 'invalid-url' - triggers nothing until we quit the application, at which point we receive:
            // "WebSocket connection to 'ws://localhost:5173/invalid-url' failed: " errors.
            // 'ws://invalid-url' - triggers onerror handler. Error message says 
            // "Websocket connection to ws://invalid-url failed: "
            // 'wss://localhost:5000/ws' - triggers onerror handler
            // `ws://${longUrl}` - triggers onerror handler
            try {
                const longUrl = 'w'.repeat(65536);
                wsRef.current = new WebSocket(`ws://localhost:5000/ws`);
                wsRef.current.onopen = () => {
                    console.log('WebSocket connection established')
                }
                wsRef.current.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    console.log('logging event itself first' + event)
                    console.log(data);
                    if (data.status === 'PROGRESS') {
                        setTrainingProgress((prev) => [...prev, {'epoch': data.epoch, 'logs': data.logs}]);
                    }
                    else if (data.status === 'SUCCESS') {
                        setAccuracy(data.test_accuracy);
                        setLoss(data.test_loss);
                        setLoading(false);
                    }
                    else if (data.status === 'ERROR'){
                        setError(`Error during training: ${data.message}`)
                        setLoading(false);
                    }
                };
        
                wsRef.current.onerror = function(error){
                    console.error(`Asynchronous error after websocket established: ${error}. Associated message: ${error.message}`);
                    setWsError(`Asynchronous error after websocket established: ${error}`);
                };
                wsRef.current.onclose = function(event){
                    console.log('WebSocket connection has closed. Attempting to reconnect in ten seconds');
                    setTimeout(connect, 10000);
                };
            } catch (error){
                console.error(`Websocket connection error (synchronous): ${error}. Associated message: ${error.message}`);
                setWsError(`Websocket connection error: ${error}`);
            }
        };
        connect();
        // cleanup function to close the websocket connection when the component is unmounted
        return () => {
            console.log("returning from useEffect")
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.close();
            }
        };
    }, []);


    // Here we're defining an asynchronous function named handleTrain using arrow function syntax.
    // This function takes an event object 'e' as a parameter, which is typically the event triggered
    // by a form submission or button click. Keyword 'async' indicates that this function is asynchronous
    // and will return a promise.
    const handleTrain = async(e) => {
        // Preventing the default form submission behavior. That is, if 'e' is a form submission event,
        // calling 'preventDefault()' will prevent the form from being submitted. This means we can handle
        // the form submission or button click programmatically ourselves via javascript.
        e.preventDefault();
        try {
            // Setting loading state variable to true, error to null, and trainingProgress to an empty array.
            // setloading(True) will cause the 'Train Model' button to display 'Training...' and become
            // unclickable instead of 'Train Model'
            setLoading(true);
            setError(null);
            setTrainingProgress([]);
            // Checking if the input values are valid. If not, setting an error message and returning early.
            if (isNaN(inputLayers) || inputLayers < 1) {
                setError('Number of layers must be a positive integer');
                setLoading(false);
                return;
            }
            if (inputUnits.some(isNaN)|| inputUnits.some(num => num < 1)) {
                setError('Units must be a comma-separated list of positive integers');
                setLoading(false);
                return;
            } 
            if (inputUnits.length !== inputLayers) {
                setError('Number of integers in list must match number of layers');
                setLoading(false);
                return;
            }
            if (isNaN(inputEpochs) || inputEpochs < 1) {
                setError('Number of epochs must be a positive integer');
                setLoading(false);
                return;
            }
            if (isNaN(inputBatchSize) || inputBatchSize < 1) {
                setError('Batch size must be a positive integer');
                setLoading(false);
                return;
            }
            // Making a POST request to the backend server using axios. The POST request is made to the
            // '/train' endpoint of the backend server. The way we have Flask backend setup is so that it runs
            // on local machine IP '127.0.0.1' and port 5000, although this may end up changing later.
            // The second argument to the 'post' method is the data we want to send to the server. This data
            // is an object with keys 'layers', 'units', 'epochs', 'batchSize', and 'optimizer'. The values of
            // these keys are the state variables defined above.
            await axios.post('http://localhost:5000/train', {
                layers: inputLayers,
                units: inputUnits,
                epochs: inputEpochs,
                batchSize: inputBatchSize,
                optimizer: inputOptimizer
            });
        } catch (err){ // more specific than just a broad error i.e catch specific types of exceptions
            // axios exceptions
            let errorMessage = 'Failed to train model: ';
            if (err.response && err.response.data && err.response.data.detail) {
                const details = err.response.data.detail;
                console.log(details)
                if (Array.isArray(details) && details.length > 0) {
                    // console.log(details[0]['loc'])
                    // console.log(details[0]['msg'])
                    // console.log(details[0]['type'])
                    // errorMessage += details.map(detail => detail.msg).join(', ');
                    errorMessage += JSON.stringify(details[0])
                } else {
                    errorMessage += JSON.stringify(details);
                }
            } else {
                errorMessage += err.message;
            }
            // consider splitting the below into one condition for when the error is from the POST request
            // and another for when the error is from before the POST request
            setError(`Some error occurred while attempting to train, could be prior to POST request or before POST request, discern based on format of error message: ${errorMessage}`);
            setLoading(false);
        }
    };

    const handleUnitsChange = (index, value) => {
        console.log('units change, index: ' + index + ' value: ' + value)
        const newUnits = [...inputUnits];
        newUnits[index] = parseInt(value) || '';
        setInputUnits(newUnits);
    };

    // add handling for non integer values
    const handleLayersChange = (value) => {
        const numLayers = parseInt(value) || '';
        if (numLayers === '' || (numLayers>=1 && numLayers<=3)){
            setInputLayers(numLayers);
            if (numLayers > inputUnits.length) {
                setInputUnits([...inputUnits, ...Array(numLayers - inputUnits.length).fill('')]);
                console.log('Expanding ' + inputUnits)
                console.log('Expanding 2 ' + [...inputUnits, ...Array(numLayers - inputUnits.length).fill('')])
            } else {
                setInputUnits(inputUnits.slice(0, numLayers));
                console.log('Contracting ' + inputUnits)
                console.log('Contracting #2 ' + inputUnits.slice(0, numLayers))
            }
        }
    };
    
    const testErrorHandler = async () => {
        try {
            const response = await axios.get('http://localhost:5000/test-error');
            console.log(response);
        }
        catch (err) {
            console.log(`Error message: ${err.message}, Error response details: ${err.response.data.detail}`);
            setError(`Error message: ${err.message}, Error response details: ${err.response.data.detail}`);
        }
    }

    return (
        <div className="App">
            <h1>CIFAR-10 Model Training UI</h1>

            {/* Form element with 'onSubmit' event handler set to the 'handleTrain' function we defined 
            earlier. 
            This means that when the form is submitted, the 'handleTrain' function will be called.
            */}
            <form onSubmit={handleTrain}>
                <div>
                    <label>Number of Layers: </label>
                    {/* Defining an input field for entering number of layers. 
                    'value={layers}' sets the initial value of the input field to the current value of 
                    the 'layers' state variable.
                    'onChange={(e) => setLayers(parseInt(e.target.value))}' updates the 'layers' state
                    when the input field value changes. */}
                    {/* <input type="number" value={inputLayers} onChange={(e) => isNaN(e.target.value) ? setInputLayers(NaN) : setInputLayers(parseInt(e.target.value))} /> */}
                    <input
                        type="number" 
                        value={inputLayers} 
                        onChange={(e) => handleLayersChange(e.target.value)} 
                        min="1" max="3"/>
                </div>
                {Array.from({ length: inputLayers }).map((_, index) => (
                    <div key={index}>
                        <label>Units in Layer {index + 1}: </label>
                        <input
                            type="number"
                            value={inputUnits[index]}
                            onChange={(e) => handleUnitsChange(index, e.target.value)}
                            min="1" max="1024"
                        />
                    </div>
                ))}
                <div>
                    <label>Number of Epochs: </label>
                    <input 
                        type="number" 
                        value={inputEpochs} 
                        onChange={(e) => setInputEpochs(parseInt(e.target.value) || '')} 
                        min = "0" max = "200"/>
                </div>
                <div>
                    <label>Batch Size: </label>
                    <input 
                        type="number" 
                        value={inputBatchSize} 
                        onChange={(e) => setInputBatchSize(parseInt(e.target.value) || '')} 
                        min = "16" max = "512" />
                </div>
                <div>
                    <label>Optimizer: </label>
                    <select 
                        value={inputOptimizer} 
                        onChange={(e) => setInputOptimizer(e.target.value)}>
                        <option value="adam">Adam</option>
                        <option value="sgd">SGD</option>
                        <option value="rmsprop">RMSprop</option>
                    </select>
                </div>
                <button type="submit" disabled = {loading}>
                    {loading ? 'Training...' : 'Train Model'}
                </button>
            </form>
            {/*  below syntax is shorthand for an if statement. For example, if 'error' is truthy
            the subsequent <p> tag is generated. If it's not, we just ignore whatever comes after
            'error' in the curly brackets */}
            {error && <p style={{ color: 'red' }}>{error}</p>}
            {wsError && <p style = {{color: 'red'}}>{wsError}</p>}
            {trainingProgress.length > 0 && (
                <div>
                    <h2>Training Progress</h2>
                    <ul>
                        {/* mapping the trainingProgress array so that 'progress' represents each item
                        in the array and index represents the item's index*/}
                        {trainingProgress.map((progress, index) => (
                            <li key={index}>
                                Epoch {progress.epoch}: {JSON.stringify(progress.logs)}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            {accuracy !== null && (
                <div>
                    <h2>Model Results</h2>
                    <p>Test Accuracy: {accuracy}</p>
                    <p>Test Loss: {loss}</p>
                </div>
            )}
            <button onClick={testErrorHandler}>Test Error Handler</button>
        </div>
    );
}

export default App
