/**
 * WayLens : Mobile Client Application
 * Features:
 * - Natural Voice Navigation Output (Web Speech API + Server TTS fallback)
 * - Voice Input (Native Web Speech Recognition + Whisper STT backend fallback)
 * - Interactive HD Canvas Map with Animated Moving Pointer
 * - Turn-by-Turn Visual Direction Badges & Route Step Progress Bar
 * - Live Camera Mode & Demo Photo Mode
 */

document.addEventListener('DOMContentLoaded', () => {
  // ── DOM References ──
  const statusBadge       = document.getElementById('statusBadge');
  const voiceToggle       = document.getElementById('voiceToggle');
  const voiceOnIcon       = document.getElementById('voiceOnIcon');
  const voiceOffIcon      = document.getElementById('voiceOffIcon');
  const instructionCard   = document.querySelector('.instruction-card');
  const instructionText   = document.getElementById('instructionText');
  const destLabel         = document.getElementById('destLabel');
  const locationLabel     = document.getElementById('locationLabel');
  const stepsBar          = document.getElementById('stepsBar');
  const stepsText         = document.getElementById('stepsText');
  const stepsProgress     = document.getElementById('stepsProgress');
  const ttsAudio          = document.getElementById('ttsAudio');

  // Destination controls
  const textDestInput     = document.getElementById('textDestInput');
  const textDestBtn       = document.getElementById('textDestBtn');
  const micBtn            = document.getElementById('micBtn');
  const micLabel          = document.getElementById('micLabel');

  // Live mode
  const cameraVideo       = document.getElementById('cameraVideo');
  const captureCanvas     = document.getElementById('captureCanvas');
  const cameraFileInput   = document.getElementById('cameraFileInput');
  const scanBtn           = document.getElementById('scanBtn');
  const autoScanBtn       = document.getElementById('autoScanBtn');
  const autoScanLabel     = document.getElementById('autoScanLabel');

  // Demo mode
  const demoUploadBtn     = document.getElementById('demoUploadBtn');
  const demoFileInput     = document.getElementById('demoFileInput');
  const demoPreview       = document.getElementById('demoPreview');
  const demoPreviewImg    = document.getElementById('demoPreviewImg');
  const demoResult        = document.getElementById('demoResult');
  const demoDetectedRoom  = document.getElementById('demoDetectedRoom');
  const demoInstruction   = document.getElementById('demoInstruction');

  // Mode tabs
  const liveTab           = document.getElementById('liveTab');
  const demoTab           = document.getElementById('demoTab');
  const livePanel         = document.getElementById('livePanel');
  const demoPanel         = document.getElementById('demoPanel');

  // Floor tabs
  const floorTabs         = document.querySelectorAll('.floor-tab');

  // End
  const endBtn            = document.getElementById('endBtn');

  // ── State ──
  let isVoiceEnabled      = localStorage.getItem('waylens_voice') !== 'false';
  let initialTotalSteps   = 0;
  let mediaRecorder       = null;
  let audioChunks         = [];
  let isRecording         = false;
  let isAutoScanning      = false;
  let autoScanTimer       = null;
  let videoStream         = null;
  let speechSynthVoice    = null;

  // ── Voice Output System (Web Speech API) ──
  function initSpeechSynthesis() {
    if (!('speechSynthesis' in window)) return;

    function populateVoices() {
      const voices = window.speechSynthesis.getVoices();
      if (!voices || voices.length === 0) return;

      // Prefer natural English voices (Google, Samantha, Natural, Microsoft)
      speechSynthVoice = voices.find(v => (v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Natural')) && v.lang.startsWith('en'))
        || voices.find(v => v.lang.startsWith('en'))
        || voices[0];
    }

    populateVoices();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = populateVoices;
    }
  }
  initSpeechSynthesis();

  /** Speak text out loud through browser TTS or backend audio */
  function speakInstruction(text, serverAudioB64 = null) {
    if (!isVoiceEnabled || !text) return;

    // Clean text of markdown / symbols for speech
    const cleanText = text.replace(/[*_#`[\]]/g, '').trim();
    if (!cleanText) return;

    // 1. Try Browser Web Speech API first (instant, high quality, natural)
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel(); // Stop any previous speech immediately
      const utterance = new SpeechSynthesisUtterance(cleanText);
      if (speechSynthVoice) utterance.voice = speechSynthVoice;
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;
      window.speechSynthesis.speak(utterance);
      return;
    }

    // 2. Fallback to Server Audio (Piper / WAV)
    if (serverAudioB64) {
      try {
        ttsAudio.src = `data:audio/wav;base64,${serverAudioB64}`;
        ttsAudio.play().catch(() => {});
      } catch (e) { /* ignore */ }
    }
  }

  // Voice Toggle Button
  function updateVoiceToggleUI() {
    if (isVoiceEnabled) {
      voiceToggle.classList.remove('off');
      voiceToggle.classList.add('on');
      voiceToggle.title = 'Voice On';
      voiceOnIcon.style.display = 'block';
      voiceOffIcon.style.display = 'none';
    } else {
      voiceToggle.classList.remove('on');
      voiceToggle.classList.add('off');
      voiceToggle.title = 'Voice Off';
      voiceOnIcon.style.display = 'none';
      voiceOffIcon.style.display = 'block';
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
      if (ttsAudio) ttsAudio.pause();
    }
  }
  updateVoiceToggleUI();

  voiceToggle.addEventListener('click', () => {
    isVoiceEnabled = !isVoiceEnabled;
    localStorage.setItem('waylens_voice', isVoiceEnabled);
    updateVoiceToggleUI();
    vibrate(40);
    if (isVoiceEnabled) {
      speakInstruction('Voice instructions enabled.');
    }
  });

  // ── Utilities ──
  function vibrate(pattern = 100) {
    if ('vibrate' in navigator) {
      try { navigator.vibrate(pattern); } catch (e) {}
    }
  }

  function setStatus(badgeText, type) {
    statusBadge.textContent = badgeText;
    statusBadge.className = `badge ${type}`;
  }

  // ── Floor Map Init ──
  if (window.FloorMap) {
    window.FloorMap.init('mapCanvas');
  }

  // Floor tab switching
  floorTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      floorTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const floor = parseInt(tab.dataset.floor);
      if (window.FloorMap) window.FloorMap.setFloor(floor);
      vibrate(30);
    });
  });

  /** Update map and progress bar from response */
  function updateMapAndProgress(data) {
    if (!window.FloorMap) return;

    // Set current position
    if (data.current_node && data.current_node !== 'rescan') {
      window.FloorMap.setCurrentNode(data.current_node);

      // Auto-switch to the correct floor tab
      const nodeFloor = window.FloorMap.getFloorForNode(data.current_node);
      if (nodeFloor) {
        window.FloorMap.setFloor(nodeFloor);
        floorTabs.forEach(t => {
          t.classList.toggle('active', parseInt(t.dataset.floor) === nodeFloor);
        });
      }
    }

    // Set destination marker
    if (data.destination_node) {
      window.FloorMap.setDestination(data.destination_node);
    }

    // Set route path & calculate remaining steps
    if (data.route_path && data.route_path.length > 0) {
      window.FloorMap.setRoute(data.route_path);

      const remaining = data.remaining_steps !== undefined ? data.remaining_steps : (data.route_path.length - 1);
      if (initialTotalSteps === 0 || remaining > initialTotalSteps) {
        initialTotalSteps = Math.max(remaining, 1);
      }

      if (remaining > 0) {
        stepsBar.classList.remove('hidden');
        stepsText.textContent = `${remaining} step${remaining > 1 ? 's' : ''} to destination`;
        const progressPct = Math.min(100, Math.max(5, ((initialTotalSteps - remaining) / initialTotalSteps) * 100));
        stepsProgress.style.width = `${progressPct}%`;
      }
    }
  }

  // ── Mode Switching ──
  liveTab.addEventListener('click', () => {
    liveTab.classList.add('active'); liveTab.setAttribute('aria-selected', 'true');
    demoTab.classList.remove('active'); demoTab.setAttribute('aria-selected', 'false');
    livePanel.classList.add('active');
    demoPanel.classList.remove('active');
    vibrate(30);
  });

  demoTab.addEventListener('click', () => {
    demoTab.classList.add('active'); demoTab.setAttribute('aria-selected', 'true');
    liveTab.classList.remove('active'); liveTab.setAttribute('aria-selected', 'false');
    demoPanel.classList.add('active');
    livePanel.classList.remove('active');
    vibrate(30);
  });

  // ── Camera Init ──
  async function initCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
    try {
      videoStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      cameraVideo.srcObject = videoStream;
      cameraVideo.setAttribute('playsinline', 'true');
      cameraVideo.setAttribute('autoplay', 'true');
      cameraVideo.muted = true;
      try { await cameraVideo.play(); } catch (e) {}
    } catch (err) {
      try {
        videoStream = await navigator.mediaDevices.getUserMedia({ video: true });
        cameraVideo.srcObject = videoStream;
        cameraVideo.setAttribute('playsinline', 'true');
        cameraVideo.setAttribute('autoplay', 'true');
        cameraVideo.muted = true;
        try { await cameraVideo.play(); } catch (e) {}
      } catch (e) {
        console.warn('Camera preview not directly streamable; Scan button will trigger photo upload.');
      }
    }
  }
  initCamera();

  // ── Set Destination (Core Handler) ──
  async function handleSetDestination(destinationStr) {
    const val = (destinationStr || '').trim();
    if (!val) return;

    vibrate(50);
    initialTotalSteps = 0;
    instructionCard.classList.add('has-instruction');
    instructionText.textContent = 'Setting destination and computing route...';
    setStatus('LISTENING', 'listening');

    const fd = new FormData();
    fd.append('destination_text', val);

    try {
      const resp = await fetch('/api/start-session', { method: 'POST', body: fd });
      const data = await resp.json();

      const instr = data.instruction || data.message || '';
      instructionText.textContent = instr;
      destLabel.textContent = data.destination_label || data.destination_node || val;

      if (resp.ok && data.status !== 'error') {
        setStatus('ACTIVE', 'active');
        if (window.FloorMap && data.destination_node) {
          window.FloorMap.setDestination(data.destination_node);
          const nodeFloor = window.FloorMap.getFloorForNode(data.destination_node);
          if (nodeFloor) {
            window.FloorMap.setFloor(nodeFloor);
            floorTabs.forEach(t => {
              t.classList.toggle('active', parseInt(t.dataset.floor) === nodeFloor);
            });
          }
        }
        speakInstruction(instr, data.audio_b64);
      } else {
        setStatus('IDLE', 'idle');
        speakInstruction(instr || 'Could not find that destination. Please try again.', data.audio_b64);
      }

      textDestInput.value = '';
    } catch (e) {
      instructionText.textContent = 'Server connection error while setting destination.';
      setStatus('IDLE', 'idle');
      speakInstruction('Server connection error. Please check your network.');
    }
  }

  // Set Destination (Text Click / Enter Key)
  textDestBtn.addEventListener('click', () => handleSetDestination(textDestInput.value));
  textDestInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleSetDestination(textDestInput.value);
  });

  // ── Voice Input (Web Speech Recognition + Whisper Fallback) ──
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  micBtn.addEventListener('click', async () => {
    if (isRecording) {
      // Stop recording if already active
      if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();
      isRecording = false;
      micBtn.classList.remove('recording');
      micLabel.textContent = 'Tap to Speak Destination';
      return;
    }

    // 1. Try Native Web Speech Recognition (Instant STT on Chrome/Safari/Android)
    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
          isRecording = true;
          micBtn.classList.add('recording');
          micLabel.textContent = 'Listening... Speak destination';
          setStatus('LISTENING', 'listening');
          vibrate([60, 40, 60]);
        };

        recognition.onresult = (event) => {
          const spokenText = event.results[0][0].transcript;
          isRecording = false;
          micBtn.classList.remove('recording');
          micLabel.textContent = 'Tap to Change Destination';
          handleSetDestination(spokenText);
        };

        recognition.onerror = (err) => {
          console.warn('SpeechRecognition error, falling back to Whisper upload:', err);
          fallbackToWhisperRecording();
        };

        recognition.onend = () => {
          isRecording = false;
          micBtn.classList.remove('recording');
          if (statusBadge.textContent === 'LISTENING') setStatus('IDLE', 'idle');
        };

        recognition.start();
        return;
      } catch (e) {
        console.warn('SpeechRecognition failed to start:', e);
      }
    }

    // 2. Fallback: Record Audio and send to Whisper STT backend
    fallbackToWhisperRecording();
  });

  async function fallbackToWhisperRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert('Microphone not supported on this browser. Please type your destination.');
      return;
    }

    try {
      const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunks = [];
      mediaRecorder = new MediaRecorder(audioStream);

      mediaRecorder.ondataavailable = e => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(audioChunks, { type: 'audio/webm' });
        audioStream.getTracks().forEach(t => t.stop());
        const fd = new FormData();
        fd.append('audio_file', blob, 'destination.webm');

        instructionText.textContent = 'Transcribing destination with Whisper AI...';
        try {
          const resp = await fetch('/api/start-session', { method: 'POST', body: fd });
          const data = await resp.json();
          const instr = data.instruction || data.message || '';
          instructionText.textContent = instr;
          destLabel.textContent = data.destination_label || data.destination_node || ':';

          if (resp.ok) {
            setStatus('ACTIVE', 'active');
            micLabel.textContent = 'Tap to Change Destination';
            if (window.FloorMap && data.destination_node) {
              window.FloorMap.setDestination(data.destination_node);
            }
            speakInstruction(instr, data.audio_b64);
          } else {
            setStatus('IDLE', 'idle');
            micLabel.textContent = 'Tap to Speak Destination';
            speakInstruction(instr || 'Could not understand audio. Please try again.', data.audio_b64);
          }
        } catch (e) {
          instructionText.textContent = 'Voice destination transcription failed.';
          micLabel.textContent = 'Tap to Speak Destination';
          setStatus('IDLE', 'idle');
        }
      };

      mediaRecorder.start();
      isRecording = true;
      vibrate(120);
      micBtn.classList.add('recording');
      micLabel.textContent = 'Recording... Tap to Stop';
      setStatus('LISTENING', 'listening');
    } catch (e) {
      alert('Microphone permission required for voice destination.');
    }
  }

  // ── Send Image Frame to /api/navigate ──
  async function sendImageFrame(imageBlob, showInDemo = false) {
    const fd = new FormData();
    fd.append('image_file', imageBlob, 'frame.jpg');

    setStatus('SCANNING', 'scanning');
    instructionCard.classList.add('has-instruction');
    instructionText.textContent = 'Detecting room and computing navigation instruction...';

    try {
      const resp = await fetch('/api/navigate', { method: 'POST', body: fd });
      const data = await resp.json();
      const instr = data.instruction || '';

      instructionText.textContent = instr;

      if (data.current_label || data.current_node) {
        locationLabel.textContent = data.current_label || data.current_node;
      }

      // Update map & progress bar
      updateMapAndProgress(data);

      if (data.status === 'arrived') {
        setStatus('ARRIVED', 'arrived');
        stopAutoScan();
        vibrate([200, 100, 200, 100, 300]);
        stepsBar.classList.add('hidden');
      } else {
        setStatus('ACTIVE', 'active');
        vibrate(80);
      }

      // Populate demo card if in Demo Mode
      if (showInDemo) {
        demoDetectedRoom.textContent = data.current_label || data.current_node || 'Unknown';
        demoInstruction.textContent = instr;
        demoResult.classList.remove('hidden');
      }

      // Speak instruction out loud
      speakInstruction(instr, data.audio_b64);

    } catch (e) {
      instructionText.textContent = 'Scan request failed. Please ensure the server is running.';
      setStatus('ACTIVE', 'active');
    }
  }

  // ── Live Mode: Scan ──
  async function scanSurroundings() {
    if (videoStream && cameraVideo.videoWidth > 0) {
      vibrate(50);
      const ctx = captureCanvas.getContext('2d');
      captureCanvas.width = cameraVideo.videoWidth || 640;
      captureCanvas.height = cameraVideo.videoHeight || 480;
      ctx.drawImage(cameraVideo, 0, 0, captureCanvas.width, captureCanvas.height);
      captureCanvas.toBlob(async (blob) => {
        if (blob) await sendImageFrame(blob, false);
      }, 'image/jpeg', 0.90);
    } else {
      vibrate(50);
      cameraFileInput.value = '';
      cameraFileInput.click();
    }
  }

  cameraFileInput.addEventListener('change', async (e) => {
    if (e.target.files && e.target.files[0]) {
      await sendImageFrame(e.target.files[0], false);
      cameraFileInput.value = '';
    }
  });

  scanBtn.addEventListener('click', scanSurroundings);

  // ── Live Mode: Auto Scan ──
  function toggleAutoScan() {
    isAutoScanning = !isAutoScanning;
    if (isAutoScanning) {
      autoScanBtn.classList.add('active');
      autoScanLabel.textContent = 'Auto: ON (5s)';
      scanSurroundings();
      autoScanTimer = setInterval(scanSurroundings, 5000);
      speakInstruction('Auto scan mode enabled. Scanning every 5 seconds.');
    } else {
      stopAutoScan();
      speakInstruction('Auto scan mode stopped.');
    }
  }

  function stopAutoScan() {
    isAutoScanning = false;
    autoScanBtn.classList.remove('active');
    autoScanLabel.textContent = 'Auto: OFF';
    if (autoScanTimer) { clearInterval(autoScanTimer); autoScanTimer = null; }
  }

  autoScanBtn.addEventListener('click', toggleAutoScan);

  // ── Demo Mode: Upload / Take Photo ──
  demoUploadBtn.addEventListener('click', () => {
    vibrate(50);
    demoFileInput.click();
  });

  demoFileInput.addEventListener('change', async (e) => {
    if (!e.target.files || !e.target.files[0]) return;
    const file = e.target.files[0];

    // Preview
    const reader = new FileReader();
    reader.onload = (ev) => {
      demoPreviewImg.src = ev.target.result;
      demoPreview.classList.remove('hidden');
    };
    reader.readAsDataURL(file);

    demoResult.classList.add('hidden');
    demoDetectedRoom.textContent = ':';
    demoInstruction.textContent = '';

    await sendImageFrame(file, true);
    demoFileInput.value = '';
  });

  // ── End Navigation ──
  endBtn.addEventListener('click', async () => {
    stopAutoScan();
    vibrate(100);
    initialTotalSteps = 0;

    try {
      const resp = await fetch('/api/end-session', { method: 'POST' });
      const data = await resp.json();

      instructionCard.classList.remove('has-instruction');
      instructionText.textContent = 'Navigation ended. Set a new destination to start again.';
      destLabel.textContent = 'Not set';
      locationLabel.textContent = 'Unknown';
      setStatus('IDLE', 'idle');
      micLabel.textContent = 'Tap to Speak Destination';
      stepsBar.classList.add('hidden');

      demoPreview.classList.add('hidden');
      demoResult.classList.add('hidden');

      if (window.FloorMap) window.FloorMap.clearRoute();

      speakInstruction('Navigation session ended. Destination cleared.', data.audio_b64);
    } catch (e) {
      instructionText.textContent = 'Failed to end session.';
    }
  });
});
