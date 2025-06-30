import { useState, useRef, useEffect, useCallback } from 'react';
import { isSTTSupported } from '../utils/speechUtils';
import { fetchWithAuth, API_BASE } from '../utils/apiUtils';

export function useSpeechToText(authenticated) {
    const [sttActive, setSttActive] = useState(false);
    const [error, setError] = useState(null);
    const sttSupported = isSTTSupported();
    const recognitionRef = useRef(null);
    const mediaStreamRef = useRef(null);
    const isRecordingRef = useRef(false);

    // Mobile-friendly microphone initialization
    useEffect(() => {
        if (authenticated && sttSupported) {
            const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

            if (!isMobile) {
                const initializeMicrophone = async () => {
                    try {
                        const mediaStream = await navigator.mediaDevices.getUserMedia({
                            audio: {
                                echoCancellation: true,
                                noiseSuppression: true,
                                autoGainControl: true
                            }
                        });
                        mediaStreamRef.current = mediaStream;
                        console.log('Desktop microphone pre-warmed successfully');
                    } catch (error) {
                        console.log('Desktop microphone pre-warm failed:', error);
                    }
                };
                initializeMicrophone().catch(error => {
                    console.error('Failed to initialize microphone:', error);
                });
            }
        }

        return () => {
            if (mediaStreamRef.current) {
                mediaStreamRef.current.getTracks().forEach(track => track.stop());
                mediaStreamRef.current = null;
            }
        };
    }, [authenticated, sttSupported]);

    const handleSTT = useCallback(async () => {
        if (!sttSupported) {
            const isMobileSafari = /iPhone|iPad|iPod/.test(navigator.userAgent) && /Safari/.test(navigator.userAgent);
            const isLocalNetworkIP = window.location.hostname.startsWith('192.168.') ||
                                    window.location.hostname.startsWith('10.') ||
                                    window.location.hostname.startsWith('172.');
            const isHTTPS = window.location.protocol === 'https:';
            const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

            if (isMobileSafari && isLocalNetworkIP && !isHTTPS) {
                setError('🔒 Mobile Safari requires HTTPS for microphone access on local networks. Please:\n\n• Use HTTPS (set HTTPS=true when starting the dev server)\n• Or access via ngrok for a secure tunnel\n• Or test on desktop for development');
            } else if (!isHTTPS && !isLocalhost) {
                setError('Speech Recognition requires HTTPS. Please access the site via HTTPS or use localhost.');
            } else {
                setError('Speech Recognition not supported in this browser. Please use Chrome, Edge, or Safari.');
            }
            return null;
        }

        if (sttActive) {
            if (recognitionRef.current && recognitionRef.current.state === 'recording') {
                recognitionRef.current.stop();
            }
            setSttActive(false);
            isRecordingRef.current = false;
            return null;
        }

        try {
            const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
            let currentStream = mediaStreamRef.current;

            const audioConstraints = isMobile ? {
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                }
            } : {
                audio: {
                    sampleRate: 48000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    latency: 0.01,
                    volume: 1.0
                }
            };

            if (!currentStream || !currentStream.active || isMobile) {
                console.log(`Requesting microphone access (${isMobile ? 'mobile' : 'desktop'} mode)`);
                currentStream = await navigator.mediaDevices.getUserMedia(audioConstraints);
                mediaStreamRef.current = currentStream;
            }

            let mediaRecorder;
            let mimeType = '';

            const formats = isMobile ? [
                'audio/webm',
                'audio/mp4',
                'audio/ogg',
                'audio/wav'
                ] : [
                'audio/webm;codecs=opus',
                'audio/mp4',
                'audio/webm',
                'audio/ogg;codecs=opus'
            ];

            for (const format of formats) {
                if (MediaRecorder.isTypeSupported(format)) {
                    mimeType = format;
                    console.log(`Selected audio format: ${format} (${isMobile ? 'mobile' : 'desktop'} mode)`);
                    break;
                }
            }

            if (!mimeType) {
                mediaRecorder = new MediaRecorder(currentStream);
                mimeType = mediaRecorder.mimeType;
                console.log(`Using browser default format: ${mimeType}`);
            } else {
                const recorderOptions = isMobile ?
                    { mimeType } :
                    { mimeType, audioBitsPerSecond: 128000 };

                mediaRecorder = new MediaRecorder(currentStream, recorderOptions);
            }

            const audioChunks = [];
            let recordingStartTime = Date.now();
            console.log(`Starting recording (${isMobile ? 'mobile' : 'desktop'} optimized), MIME type: ${mimeType}`);

            setSttActive(true);
            isRecordingRef.current = true;
            recognitionRef.current = mediaRecorder;

            const dataInterval = isMobile ? 100 : 10;
            mediaRecorder.start(dataInterval);

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && isRecordingRef.current) {
                    audioChunks.push(event.data);
                }
            };

            return new Promise((resolve) => {
                mediaRecorder.onstop = async () => {
                    const totalDuration = Date.now() - recordingStartTime;

                    try {
                        const minDuration = isMobile ? 500 : 300;
                        if (totalDuration < minDuration || audioChunks.length === 0) {
                            setError(`Recording too short. Please hold the button for at least ${minDuration/1000} seconds and speak clearly.`);
                            setSttActive(false);
                            resolve(null);
                            return;
                        }

                        const audioBlob = new Blob(audioChunks, { type: mimeType });

                        console.log('Audio blob created:', {
                            size: audioBlob.size,
                            type: audioBlob.type,
                            duration: totalDuration,
                            chunks: audioChunks.length,
                            platform: isMobile ? 'mobile' : 'desktop'
                        });

                        const minSize = isMobile ? 1000 : 1500;
                        if (audioBlob.size < minSize) {
                            setError('Recording failed or too short. Please try again and speak louder.');
                            setSttActive(false);
                            resolve(null);
                            return;
                        }

                        const reader = new FileReader();
                        reader.onload = async () => {
                            try {
                                const base64Audio = reader.result.split(',')[1];

                                if (!isMobile) {
                                    const debugAudioUrl = URL.createObjectURL(audioBlob);
                                    const debugLink = document.createElement('a');
                                    debugLink.href = debugAudioUrl;
                                    debugLink.download = `debug_audio_${Date.now()}.webm`;
                                    debugLink.style.display = 'none';
                                    document.body.appendChild(debugLink);
                                    debugLink.click();
                                    document.body.removeChild(debugLink);
                                    console.log('Debug: Audio file saved for inspection');
                                }

                                const response = await fetchWithAuth(`${API_BASE}/transcribe/`, {
                                    method: 'POST',
                                    body: JSON.stringify({
                                        audio: base64Audio,
                                        model: 'gpt-4o-mini-transcribe',
                                        format: mimeType
                                    })
                                });

                                if (!response.ok) {
                                    const errorData = await response.json();
                                    throw new Error(errorData.detail || 'Failed to transcribe audio');
                                }

                                const data = await response.json();

                                if (data.text && data.text.trim()) {
                                    const transcribedText = data.text.trim();
                                    console.log('Transcription successful:', transcribedText);
                                    resolve(transcribedText);
                                } else {
                                    setError('No speech detected. Please try speaking more clearly.');
                                    resolve(null);
                                }

                            } catch (error) {
                                console.error('Transcription error:', error);
                                setError(error.message || 'Failed to transcribe audio. Please try again.');
                                resolve(null);
                            }
                        };

                        reader.onerror = () => {
                            setError('Failed to process audio data. Please try again.');
                            resolve(null);
                        };

                        reader.readAsDataURL(audioBlob);

                    } catch (error) {
                        console.error('Audio processing error:', error);
                        setError('Failed to process audio. Please try again.');
                        resolve(null);
                    } finally {
                        setSttActive(false);
                        isRecordingRef.current = false;

                        if (isMobile && mediaStreamRef.current) {
                            mediaStreamRef.current.getTracks().forEach(track => track.stop());
                            mediaStreamRef.current = null;
                        }
                    }
                };
            });

        } catch (error) {
            setSttActive(false);
            isRecordingRef.current = false;
            console.error('Microphone access error:', error);

            if (error.name === 'NotAllowedError') {
                setError('Microphone access denied. Please allow microphone access in your browser settings and reload the page.');
            } else if (error.name === 'NotFoundError') {
                setError('No microphone found. Please connect a microphone and try again.');
            } else if (error.name === 'NotSupportedError') {
                setError('Audio recording not supported in this browser. Please use Chrome, Edge, or Safari.');
            } else if (error.name === 'NotReadableError') {
                setError('Microphone is being used by another application. Please close other apps using the microphone.');
            } else {
                setError(`Failed to start audio recording: ${error.message}. Please check your microphone and try again.`);
            }
            return null;
        }
    }, [sttSupported, sttActive]);

    const clearError = useCallback(() => setError(null), []);

    return {
        sttActive,
        sttSupported,
        error,
        handleSTT,
        clearError
    };
}
