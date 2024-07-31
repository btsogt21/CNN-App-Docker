import React from 'react'
import { useNavigate } from 'react-router-dom'

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