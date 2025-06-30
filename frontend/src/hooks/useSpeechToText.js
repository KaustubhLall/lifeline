// Hook for managing speech-to-text recording and transcription
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

    // Pre-warm desktop microphone to reduce latency
    useEffect(() => {
        if (authenticated && sttSupported) {
            const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

            if (!isMobile) {
                const initializeMicrophone = async () => {
                    try {
                        const stream = await navigator.mediaDevices.getUserMedia({
                            audio: {
                                echoCancellation: true,
                                noiseSuppression: true,
                                autoGainControl: true
                            }
                        });
                        mediaStreamRef.current = stream;
                    } catch {
                        // Ignore initialization errors
                    }
                };
                initializeMicrophone();
            }
        }

        return () => {
            // Stop any active media tracks on cleanup
            if (mediaStreamRef.current) {
                mediaStreamRef.current.getTracks().forEach(t => t.stop());
                mediaStreamRef.current = null;
            }
        };
    }, [authenticated, sttSupported]);

    // Start or stop recording and return transcribed text
    const handleSTT = useCallback(async () => {
        console.log('handleSTT called in useSpeechToText hook', { sttSupported, sttActive });

        if (!sttSupported) {
            console.log('STT not supported, showing error');
            // Provide guidance when unsupported or insecure
            const isMobileSafari = /iPhone|iPad/.test(navigator.userAgent) && /Safari/.test(navigator.userAgent);
            const isHTTPS = window.location.protocol === 'https:';
            const isLocal = ['localhost', '127.0.0.1'].includes(window.location.hostname);

            if (isMobileSafari && !isHTTPS) {
                setError('Mobile Safari requires HTTPS for microphone access.');
            } else if (!isHTTPS && !isLocal) {
                setError('Speech Recognition requires HTTPS.');
            } else {
                setError('Speech Recognition not supported in this browser.');
            }
            return null;
        }

        if (sttActive) {
            console.log('Stopping active recording');
            // Stop ongoing recording
            const recorder = recognitionRef.current;
            if (recorder?.state === 'recording') recorder.stop();
            setSttActive(false);
            isRecordingRef.current = false;
            return null;
        }

        console.log('Starting new recording...');
        setSttActive(true);

        try {
            // Request or reuse media stream
            const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
            let stream = mediaStreamRef.current;

            if (!stream || !stream.active || isMobile) {
                const constraints = {
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true,
                        sampleRate: isMobile ? undefined : 48000
                    }
                };
                stream = await navigator.mediaDevices.getUserMedia(constraints);
                mediaStreamRef.current = stream;
            }

            // Select supported audio format for recorder
            const formats = isMobile
                ? ['audio/webm', 'audio/mp4', 'audio/ogg', 'audio/wav']
                : ['audio/webm;codecs=opus', 'audio/mp4', 'audio/webm', 'audio/ogg;codecs=opus'];
            let mimeType = formats.find(f => MediaRecorder.isTypeSupported(f)) || '';
            const recorder = new MediaRecorder(stream, mimeType ? { mimeType, audioBitsPerSecond: isMobile ? undefined : 128000 } : undefined);

            // Collect audio chunks
            const audioChunks = [];
            isRecordingRef.current = true;
            recognitionRef.current = recorder;
            recorder.start(isMobile ? 100 : 10);

            recorder.ondataavailable = e => { if (e.data.size && isRecordingRef.current) audioChunks.push(e.data); };

            return new Promise(resolve => {
                recorder.onstop = async () => {
                    setSttActive(false);
                    isRecordingRef.current = false;

                    if (isMobile && mediaStreamRef.current) {
                        mediaStreamRef.current.getTracks().forEach(t => t.stop());
                        mediaStreamRef.current = null;
                    }

                    const audioBlob = new Blob(audioChunks, { type: recorder.mimeType });

                    // Validate recording length and size
                    if (audioBlob.size < (isMobile ? 1000 : 1500)) {
                        setError('Recording too short or failed.');
                        return resolve(null);
                    }

                    // Convert to base64 and send to API
                    const reader = new FileReader();
                    reader.onload = async () => {
                        try {
                            const base64Audio = reader.result.split(',')[1];
                            const resp = await fetchWithAuth(`${API_BASE}/transcribe/`, {
                                method: 'POST',
                                body: JSON.stringify({
                                    audio: base64Audio,
                                    model: 'gpt-4o-mini-transcribe',
                                    format: recorder.mimeType
                                })
                            });
                            const data = await resp.json();
                            resolve(data.text?.trim() || null);
                        } catch (err) {
                            setError(err.message || 'Transcription failed.');
                            resolve(null);
                        }
                    };
                    reader.onerror = () => { setError('Audio processing error.'); resolve(null); };
                    reader.readAsDataURL(audioBlob);
                };
            });

        } catch (e) {
            console.error('Media access error:', e);
            // Handle media access errors
            setSttActive(false);
            isRecordingRef.current = false;
            const msgMap = {
                'NotAllowedError': 'Microphone access denied.',
                'NotFoundError': 'No microphone found.',
                'NotSupportedError': 'Audio recording not supported.',
                'NotReadableError': 'Microphone unavailable.'
            };
            setError(msgMap[e.name] || `Recording error: ${e.message}`);
            return null;
        }
    }, [sttSupported, sttActive]);

    const clearError = useCallback(() => setError(null), []);

    return { sttActive, sttSupported, error, handleSTT, clearError };
}
