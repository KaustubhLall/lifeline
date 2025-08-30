import React, { useState } from 'react';
import '../styles/components/DebugPanel.css';

function DebugPanel({ temperature, setTemperature }) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className="debug-panel">
            <button onClick={() => setIsOpen(!isOpen)} className="debug-toggle-button">
                Debug Settings <i className={`bi bi-chevron-${isOpen ? 'down' : 'right'}`}></i>
            </button>
            {isOpen && (
                <div className="debug-content">
                    <div className="debug-control">
                        <label htmlFor="temperature">Temperature: {temperature.toFixed(1)}</label>
                        <input
                            type="range"
                            id="temperature"
                            min="0"
                            max="2"
                            step="0.1"
                            value={temperature}
                            onChange={(e) => setTemperature(parseFloat(e.target.value))}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}

export default DebugPanel;
