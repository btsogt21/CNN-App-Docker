import { useEffect, useState } from 'react'
import './App.css'
import axios from 'axios'
import io from 'socket.io-client'

const socket = io('http://localhost:5000')

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
    const [layers, setLayers] = useState(3);
    const [units, setUnits] = useState([32, 64, 128]);
    const [epochs, setEpochs] = useState(50);
    const [batchSize, setBatchSize] = useState(32);
    const [optimizer, setOptimizer] = useState('adam');
    const [accuracy, setAccuracy] = useState(null);
    const [loss, setLoss] = useState(null);

    // Defining additional state variables to indicate whether model is currently training, as well
    // as if there is an error during training. 
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Defining one more state variable to store training progress data/outputs to show the user.
    const [trainingProgress, setTrainingProgress] = useState(0);

    // Purpose of useEffect

    // useEffect is a React hook that allows you to perform side effects in function components. 
    // Side effects can be data fetching, subscriptions, or manually changing the DOM in React 
    // components.

    // It takes two arguments: a function that contains the side effect logic and an optional array 
    // of dependencies. React will re-run the side effect function whenever one of the dependencies 
    // has changed. <useEffect(effectFunction, [dependencies]);>

    // The side effect function can optionally return a cleanup function that React will call when 
    // the component unmounts or before re-running the side effect due to changes in dependencies

    // The logic here is that we want to listen for the 'training_progress' event from the backend
    // via the websocket connection. We then update the 'trainingProgress' state variable with the
    // progress data from the event by calling the 'setTrainingProgress' function which adds the
    // progress data to the 'trainingProgress' array.

    // Useful if we want to keep a history of all the progress updates received over time for each 
    // epoch.

    // ( () => {} ). Inside the paranthesis is the arrow function syntax. This is
    // basically saying that the first argument of useEffect (that is, effectFunction) is a function 
    // defined as follows:
    // () => { ... }, where () contains the parameters to the function and {...} contains the
    // body of the function.
    useEffect(() => {
        // listening for the 'training_progress' event, then defining a callback function to 
        // trigger when the event is received. The callback function takes a 'data' parameter. This
        // 'data' parameter is received from the server when it sends a message of type 'training_progress'.
        // The socket.on method then receives this data and passes it to the callback function as an argument.
        // The name 'data' is arbitrary. You could name it anything and it would still represent the 
        // data sent alongside the 'training_progress' event.
        socket.on('training_progress', (data) => {
            // Updating the 'trainingProgress' state variable with the progress data from the event.
            // This works by calling the state updater function 'setTrainingProgress' with the previous
            // state as an argument. Naming choice of the argument is arbitrary here as React invokes
            // the function with the previous state as an argument. That's just how React works when 
            // you call a state updater function. As for '[...prev, data]', you can think of
            // it as an array where '...prev' indicates that all elements of the previous state array
            // are still present, and we're just adding the new progress data 'data.progress' to the
            // end.
            setTrainingProgress((prev) => [...prev, data]);
        });

        // Returning a cleanup function that will be called when the component unmounts or when the 
        // useEffect hook is run again. This is important because we don't want to keep listening 
        // for the 'training_progress' event when the component is no longer in use. This is a good 
        // practice to avoid memory leaks.
        return () => {
            socket.off('training_progress');
        };
    }, []
    );

    // Here we're defining an asynchronous function named handleTrain using arrow function syntax.
    // This function takes an event object 'e' as a parameter, which is typically the event triggered
    // by a form submission or button click. Keyword 'async' indicates that this function is asynchronous
    // and will return a promise.
    const handleTrain = async(e) => {
        // Preventing the default form submission behavior. That is, if 'e' is a form submission event,
        // calling 'preventDefault()' will prevent the form from being submitted. This means we can handle
        // the form submission or button click programmatically ourselves via javascript.
        e.preventDefault();

        setLoading(true);
        setError(null);
        setTrainingProgress([]);
        try {
            // Making a POST request to the backend server using axios. The POST request is made to the
            // '/train' endpoint of the backend server. The way we have Flask backend setup is so that it runs
            // on local machine IP '127.0.0.1' and port 5000, although this may end up changing later.
            // The second argument to the 'post' method is the data we want to send to the server. This data
            // is an object with keys 'layers', 'units', 'epochs', 'batchSize', and 'optimizer'. The values of
            // these keys are the state variables defined above.
            const response = await axios.post('http://localhost:5000/train', {
                layers: layers,
                units: units,
                epochs: epochs,
                batchSize: batchSize,
                optimizer: optimizer
            });
            // Using the aforementioned 'setAccuracy' and 'setLoss' functions to update the accuracy and loss
            // with data from the response object
            setAccuracy(response.data.accuracy);
            setLoss(response.data.loss);
        } catch (err){
            setError('Failed to train model: ${err.message}');
        } finally {
            setLoading(false);
        }

    // Mock data to be sent to backend
    // const data = {
    //     layers: layers,
    //     units: units,
    //     epochs: epochs,
    //     batchSize: batchSize,
    //     optimizer: optimizer
    //   };

    // console.log("Data to be sent to backend", JSON.stringify(data, null, 2));

    // Mock response from backend
    // const mockResponse = {
    //     data: {
    //         accuracy: 0.85,
    //         loss: 0.35
    //     }
    // };

    // console.log("Response from backend", JSON.stringify(mockResponse, null, 2));

    // setAccuracy(mockResponse.data.accuracy);
    // setLoss(mockResponse.data.loss);

    };
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
                    <input type="number" value={layers} onChange={(e) => setLayers(parseInt(e.target.value))} />
                </div>
                {/* Commenting out control over node count for now. Will return to this later. */}
                {/* <div>
                    <label>Units in Layers (comma-separated): </label>
                    <input
                        type="text"
                        value={units.join(',')}
                        onChange={(e) => setUnits(e.target.value.split(',').map(Number))}
                    />
                </div> */}
                <div>
                    <label>Number of Epochs: </label>
                    <input type="number" value={epochs} onChange={(e) => setEpochs(parseInt(e.target.value))} />
                </div>
                {/* Commenting out control over batch size for now, will return later */}
                {/* <div>
                    <label>Batch Size: </label>
                    <input type="number" value={batchSize} onChange={(e) => setBatchSize(parseInt(e.target.value))} />
                </div> */}
                <div>
                    <label>Optimizer: </label>
                    <select value={optimizer} onChange={(e) => setOptimizer(e.target.value)}>
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
            {trainingProgress.length > 0 && (
                <div>
                    <h2>Training Progress</h2>
                    <ul>
                        {/* mapping the trainingProgress array so that 'progress' represents each item
                        in the array and index represents the item's index*/}
                        {trainingProgress.map((progress, index) => (
                            <li key={index}>
                                Epoch {progress.epoch + 1}: {JSON.stringify(progress.logs)}
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
        </div>
    );
}

export default App
