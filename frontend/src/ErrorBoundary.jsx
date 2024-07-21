import React from 'react'
import { useNavigate } from 'react-router-dom'

// class ErrorBoundary extends React.Component {
//     constructor(props) {
//         super(props)
//         this.state = { hasError: false }
//     }

//     static getDerivedStateFromError(error) {
//     // Update state so the next render will show the fallback UI.
//         return { hasError: true }
//     }

//     componentDidCatch(error, errorInfo) {
//     // You can also log the error to an error reporting service
//         console.error("Error Boundary Caught an Error:", error, errorInfo);
//     }

//     render() {
//         if (this.state.hasError) {
//         return <h1>Something went wrong. Please try again later.</h1>
//         }
//         return this.props.children
//     }
// }

const ErrorBoundary = () => {
    const navigate = useNavigate();

    const handleRetry = () => {
        navigate('/') // navigate back to the home page)
    }

    return (
        <div>
            <h1>Something went wrong. The backend is unavailable. Please try again later.</h1>
            <button onClick={handleRetry}>Retry</button>
        </div>
    )
}

export default ErrorBoundary;