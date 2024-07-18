import React, { useEffect } from 'react';

const ErrorTestComponent = () => {
    useEffect(() => {
        throw new Error("Deliberate Test Error in ErrorTestComponent");
    }, []);

    return <div>ErrorTestComponent</div>;
};

export default ErrorTestComponent;
