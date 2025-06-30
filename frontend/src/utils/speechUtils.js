// Speech-to-text support detection utility
export function isSTTSupported() {
    // Check basic browser support first
    const hasMediaDevices = typeof window !== 'undefined' &&
        ('mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices);

    const hasMediaRecorder = typeof MediaRecorder !== 'undefined';

    // Detect mobile Safari specifically
    const isMobileSafari = /iPhone|iPad|iPod/.test(navigator.userAgent) && /Safari/.test(navigator.userAgent);
    const isAndroid = /Android/.test(navigator.userAgent);
    const isMobile = isMobileSafari || isAndroid || /Mobile/.test(navigator.userAgent);

    // Check if we're in a secure context (HTTPS or localhost)
    const isSecureContext = window.isSecureContext === true ||
        window.location.protocol === 'https:' ||
        window.location.hostname === 'localhost' ||
        window.location.hostname === '127.0.0.1';

    // For local network IPs, check if protocol is secure
    const isLocalNetworkIP = window.location.hostname.match(/^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)/);
    const isSecureProtocol = window.location.protocol === 'https:';

    // Log detailed support information for debugging
    console.log('STT Support Check:', {
        hasMediaDevices,
        hasMediaRecorder,
        isSecureContext,
        isLocalNetworkIP,
        isSecureProtocol,
        isMobile,
        protocol: window.location.protocol,
        hostname: window.location.hostname,
        userAgent: navigator.userAgent
    });

    // Desktop browsers: be more permissive for local development
    if (!isMobile) {
        // Allow STT on desktop regardless of protocol for local development
        if (window.location.hostname === 'localhost' ||
            window.location.hostname === '127.0.0.1' ||
            isLocalNetworkIP) {
            console.log('Desktop local development detected - allowing STT regardless of protocol');
            return hasMediaDevices && hasMediaRecorder;
        }
    }

    // Mobile devices: enforce stricter security for mic access
    if (isMobile && isLocalNetworkIP && !isSecureProtocol) {
        console.warn('Mobile device on local network without HTTPS - microphone access likely blocked by browser security policy');
        return false;
    }

    // For production or other contexts, require secure context
    const basicSupport = hasMediaDevices && hasMediaRecorder && isSecureContext;

    if (!basicSupport) {
        console.warn('Speech Recognition not supported: missing requirements');
    }

    return basicSupport;
}
