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
    const isSecureContext = window.isSecureContext || window.location.protocol === 'https:' ||
                           window.location.hostname === 'localhost' ||
                           window.location.hostname === '127.0.0.1';

    // For local network IPs, only allow on desktop browsers or with HTTPS
    const isLocalNetworkIP = window.location.hostname.startsWith('192.168.') ||
                            window.location.hostname.startsWith('10.') ||
                            window.location.hostname.startsWith('172.');

    // Log detailed support information for debugging
    console.log('STT Support Check:', {
        hasMediaDevices,
        hasMediaRecorder,
        isSecureContext,
        isLocalNetworkIP,
        isMobileSafari,
        isAndroid,
        isMobile,
        protocol: window.location.protocol,
        hostname: window.location.hostname,
        userAgent: navigator.userAgent
    });

    // Mobile Safari on local network IPs requires HTTPS
    if (isMobileSafari && isLocalNetworkIP && !isSecureContext) {
        console.warn('Mobile Safari detected on local network without HTTPS - microphone access blocked by browser security policy');
        return false;
    }

    // For local development, be more permissive on desktop but warn about security
    const basicSupport = hasMediaDevices && hasMediaRecorder;

    if (basicSupport && !isSecureContext && !isMobile) {
        console.warn('Speech Recognition: Running in non-secure context. HTTPS is recommended for production.');
    }

    return basicSupport;
}
