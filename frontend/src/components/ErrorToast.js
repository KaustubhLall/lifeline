import React from 'react';

function ErrorToast({message, onClose}) {
    return (
        <div className="toast show position-fixed top-0 end-0 m-3" role="alert" style={{zIndex: 1050}}>
            <div className="toast-header bg-danger text-white">
                <strong className="me-auto">Error</strong>
                <button
                    type="button"
                    className="btn-close btn-close-white"
                    onClick={onClose}
                    aria-label="Close"
                ></button>
            </div>
            <div className="toast-body bg-danger text-white">
                {message}
            </div>
        </div>
    );
}

export default ErrorToast;
