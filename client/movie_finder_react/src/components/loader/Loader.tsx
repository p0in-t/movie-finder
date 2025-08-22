import { useEffect } from 'react';
import './Loader.css'

const Loader = () => {
    useEffect(() => {
        const style = document.createElement("style");
        style.innerHTML = `
      @keyframes pulseColors {
        0%, 100% {
          background-color: rgba(26, 26, 26, 1);
        }
        50% {
          background-color: rgba(33, 33, 33, 1);
        }
      }

      @keyframes pulseColorsText {
        0%, 100% {
          color: rgba(199, 199, 199, 1);
        }
        50% {
          color: rgba(255, 255, 255, 1);
        }
      }
    `;
        document.head.appendChild(style);
        return () => {
            document.head.removeChild(style);
        };
    }, []);

    return (
        <div>
            <div
                className="h-screen w-full"
                style={{
                    animation: "pulseColors 2s ease-in-out infinite",
                }}
            >
                <div className="loader dark flex items-center justify-center h-full w-full"
                    style={{
                        animation: "pulseColorsText 1s ease-in-out infinite",
                    }}>
                    <div className="skeleton w-48 h-6 rounded-md font-semibold text-4xl">Loading...</div>
                </div>
            </div>
        </div>
    );
};

export default Loader;