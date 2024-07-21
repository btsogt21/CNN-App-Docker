// currently two active console.log, this is to confirm that websocket is receiving MessaveEvent object
// and passing it onto the onmessage event handler and its associated function.

import { useEffect, useState, useRef } from 'react';
import './App.css';
import axios from 'axios';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './HomePage';
import ErrorBoundary from './ErrorBoundary';



// App component is a functional component (that is, a component defined as a function instead of as
// an extension of the React.Component class). It is the main component of the application and is
// responsible for rendering the UI and handling user interactions. Mounting refers to the process
// of creating an instance of a component and inserting it into the DOM. Unmounting refers to the
// process of removing a component instance from the DOM. The App component is mounted when the
// application is loaded in the browser and unmounted when the application is closed or navigated
// away from.

function App() {
    return (
        <Router>
            <Routes>
                <Route path='/error-boundary' element = {<ErrorBoundary/>}/>
                <Route path='/' element = {<HomePage/>}/>
            </Routes>
        </Router>
    );
}

export default App
