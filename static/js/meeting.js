;(() => {
  const root = document.querySelector('.meeting-shell')
  if (!root || root.dataset.meetingReady === '1') return
  root.dataset.meetingReady = '1'

  const meetingId = root.dataset.meetingId
  const grid = document.getElementById('video-grid')
  const status = document.getElementById('connection-status')
  const micBtn = document.getElementById('mic-btn')
  const camBtn = document.getElementById('cam-btn')
  const quality = document.getElementById('quality')
  const recordingQuality = document.getElementById('recording-quality')
  const endBtn = document.getElementById('end-btn')
  const recordBtn = document.getElementById('record-btn')
  const copyBtn = document.getElementById('copy-link')
  const whatsappBtn = document.getElementById('whatsapp-link')
  const emailBtn = document.getElementById('email-link')
  const leaveBtn = document.getElementById('leave-btn')
  const layoutBtn = document.getElementById('layout-btn')
  const splitVerticalBtn = document.getElementById('split-vertical-btn')
  const splitSquareBtn = document.getElementById('split-square-btn')
  const toast = document.getElementById('toast')
  const peers = new Map()
  const names = new Map()
  const hostPeers = new Set()
  let socket = null
  let localStream = null
  let localPeerId = null
  let isHost = false
  let started = false
  let stopping = false
  let recorder = null
  let recorderStream = null
  let chunkSequence = 0
  let pendingChunkWrites = new Set()
  let recordingWanted = false
  let currentLayout = 'grid'
  let waitingTimer = null
  const rtcConfig = { iceServers: [] }

  const QUALITY = {
    saver: { width: 320, height: 240, fps: 10, bitrate: 180000 },
    low: { width: 640, height: 480, fps: 15, bitrate: 450000 },
    hd: { width: 1280, height: 720, fps: 20, bitrate: 900000 }
  }
  const RECORDING = {
    saver: { width: 320, height: 240, fps: 8, bitrate: 260000 },
    low: { width: 640, height: 480, fps: 12, bitrate: 550000 },
    hd: { width: 1280, height: 720, fps: 15, bitrate: 1000000 },
    mobile: { width: 540, height: 960, fps: 15, bitrate: 850000 }
  }

  function notify (message) {
    toast.textContent = message
    toast.classList.add('show')
    clearTimeout(notify.t)
    notify.t = setTimeout(() => toast.classList.remove('show'), 2600)
  }
  function currentToken () {
    return localStorage.getItem('vp_access') || ''
  }
  function routeWithId (template, id) {
    return template.replace(
      '00000000-0000-0000-0000-000000000000',
      encodeURIComponent(id)
    )
  }
  function wsUrl () {
    const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
    return `${scheme}://${location.host}${
      window.VP_WS.meetingPrefix
    }${encodeURIComponent(meetingId)}/?token=${encodeURIComponent(
      currentToken()
    )}`
  }
  function escapeHtml (s) {
    return String(s).replace(
      /[&<>'"]/g,
      c =>
        ({
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          "'": '&#39;',
          '"': '&quot;'
        }[c])
    )
  }

  function makeVideo (id, name, stream, local = false, peerIsHost = false) {
    if (!id) return null
    const safeId = id.replace(/[^a-zA-Z0-9_-]/g, '_')
    let card = document.getElementById(`peer-${safeId}`)
    if (!card) {
      card = document.createElement('article')
      card.className = 'video-card'
      card.id = `peer-${safeId}`
      card.dataset.peerId = id
      card.innerHTML = `<video autoplay playsinline ${
        local ? 'muted' : ''
      }></video><div class="video-meta"><span class="participant-name">${escapeHtml(
        name
      )}</span><span class="peer-state">Connected</span></div>`
      grid.querySelector('.empty-state')?.remove()
      grid.appendChild(card)
    }
    card.classList.toggle('is-host', local ? isHost : peerIsHost)
    const video = card.querySelector('video')
    if (video.srcObject !== stream) video.srcObject = stream
    updateLayoutAvailability()
    return card
  }

  function findCard (id) {
    const safeId = String(id || '').replace(/[^a-zA-Z0-9_-]/g, '_')
    return document.getElementById(`peer-${safeId}`)
  }

  function removeVideo (id) {
    findCard(id)?.remove()
    updateLayoutAvailability()
    if (!participantCount())
      grid.innerHTML =
        '<div class="empty-state"><div class="loader"></div><p>Waiting for participants…</p></div>'
  }
  function participantCount () {
    return grid.querySelectorAll('.video-card').length
  }

  function updateLayoutAvailability () {
    const count = participantCount()
    grid.dataset.count = String(count)
    const splitAllowed = count > 0 && count <= 3
    splitVerticalBtn.disabled = !splitAllowed
    splitSquareBtn.disabled = !splitAllowed
    if (!splitAllowed && currentLayout.startsWith('split-'))
      currentLayout = 'grid'
    layoutBtn.classList.toggle('active', currentLayout === 'portrait')
    splitVerticalBtn.classList.toggle(
      'active',
      currentLayout === 'split-vertical'
    )
    splitSquareBtn.classList.toggle('active', currentLayout === 'split-square')
    applyLayout()
  }

  function applyLayout () {
    grid.classList.remove(
      'square-mode',
      'portrait-mode',
      'split-vertical-mode',
      'split-square-mode'
    )
    if (currentLayout === 'portrait') grid.classList.add('portrait-mode')
    else if (currentLayout === 'split-vertical')
      grid.classList.add('split-vertical-mode')
    else if (currentLayout === 'split-square')
      grid.classList.add('split-square-mode')
    else grid.classList.add('square-mode')
  }

  async function getLocalMedia (mode = 'saver') {
    const q = QUALITY[mode]
    if (localStream) {
      const track = localStream.getVideoTracks()[0]
      if (track) {
        try {
          await track.applyConstraints({
            width: { ideal: q.width, max: q.width },
            height: { ideal: q.height, max: q.height },
            frameRate: { ideal: q.fps, max: q.fps }
          })
          await tuneSenders(q)
          return
        } catch {}
      }
    }
    localStream?.getTracks().forEach(t => t.stop())
    localStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      },
      video: {
        width: { ideal: q.width, max: q.width },
        height: { ideal: q.height, max: q.height },
        frameRate: { ideal: q.fps, max: q.fps }
      }
    })
    if (localPeerId) makeVideo(localPeerId, 'You', localStream, true, isHost)
    for (const pc of peers.values()) {
      for (const sender of pc.getSenders()) {
        const replacement = localStream
          .getTracks()
          .find(t => t.kind === sender.track?.kind)
        if (replacement) {
          try {
            await sender.replaceTrack(replacement)
          } catch {}
        }
      }
    }
    await tuneSenders(q)
  }

  async function tuneSenders (q) {
    for (const pc of peers.values()) {
      for (const sender of pc.getSenders()) {
        if (!sender.track) continue
        const params = sender.getParameters()
        params.encodings = params.encodings?.length ? params.encodings : [{}]
        params.encodings[0].maxBitrate = q.bitrate
        params.encodings[0].maxFramerate = q.fps
        try {
          await sender.setParameters(params)
        } catch {}
      }
    }
  }

  async function createPeer (peerId, offer = false) {
    if (!peerId || peerId === localPeerId) return null
    if (peers.has(peerId)) {
      const existing = peers.get(peerId)
      if (offer && existing.signalingState === 'stable') {
        const desc = await existing.createOffer({
          offerToReceiveAudio: true,
          offerToReceiveVideo: true
        })
        await existing.setLocalDescription(desc)
        send({ type: 'offer', target: peerId, sdp: existing.localDescription })
      }
      return existing
    }
    const pc = new RTCPeerConnection(rtcConfig)
    peers.set(peerId, pc)
    localStream?.getTracks().forEach(track => pc.addTrack(track, localStream))
    pc.onicecandidate = e => {
      if (e.candidate)
        send({ type: 'ice_candidate', target: peerId, candidate: e.candidate })
    }
    pc.ontrack = e => {
      const stream = e.streams[0] || new MediaStream([e.track])
      makeVideo(
        peerId,
        names.get(peerId) || 'Participant',
        stream,
        false,
        hostPeers.has(peerId)
      )
    }
    pc.onconnectionstatechange = () => {
      if (pc.connectionState === 'failed' || pc.connectionState === 'closed')
        removePeer(peerId)
      if (pc.connectionState === 'disconnected')
        setTimeout(() => {
          if (pc.connectionState !== 'connected') removePeer(peerId)
        }, 2000)
    }
    if (offer) {
      const desc = await pc.createOffer({
        offerToReceiveAudio: true,
        offerToReceiveVideo: true
      })
      await pc.setLocalDescription(desc)
      send({ type: 'offer', target: peerId, sdp: pc.localDescription })
    }
    return pc
  }

  function removePeer (peerId) {
    const pc = peers.get(peerId)
    if (pc) {
      try {
        pc.close()
      } catch {}
      peers.delete(peerId)
    }
    names.delete(peerId)
    hostPeers.delete(peerId)
    removeVideo(peerId)
  }
  function send (data) {
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(data))
  }

  async function loadRtcConfig () {
    try {
      const r = await vpFetch(window.VP_URLS.meetingRtcConfig)
      if (r.ok) {
        const d = await r.json()
        rtcConfig.iceServers = d.ice_servers || []
      }
    } catch {}
  }

  async function connect () {
    if (
      socket &&
      [WebSocket.OPEN, WebSocket.CONNECTING].includes(socket.readyState)
    )
      return
    socket = new WebSocket(wsUrl())
    socket.onopen = () => {
      status.textContent = 'Connected · waiting for participants'
    }
    socket.onclose = () => {
      if (!stopping && !document.hidden)
        status.textContent = 'Connection paused'
    }
    socket.onerror = () => {
      status.textContent = 'Network issue · retrying…'
    }
    socket.onmessage = async e => {
      const m = JSON.parse(e.data)
      if (m.type === 'connected') {
        localPeerId = m.peer_id
        isHost = !!m.is_host
        names.set(localPeerId, 'You')
        if (isHost) hostPeers.add(localPeerId)
        endBtn.classList.toggle('hidden', !isHost)
        recordBtn.classList.toggle('hidden', !isHost)
        recordingQuality
          .closest('.recording-select')
          ?.classList.toggle('hidden', !isHost)
        leaveBtn.classList.toggle('hidden', isHost)
        if (localStream)
          makeVideo(localPeerId, 'You', localStream, true, isHost)
        return
      }
      if (m.type === 'participant_joined') {
        if (m.peer_id === localPeerId) return
        names.set(m.peer_id, m.name || 'Participant')
        if (m.is_host) hostPeers.add(m.peer_id)
        status.textContent = `Connected · ${
          participantCount() + 1
        } participant${participantCount() + 1 === 1 ? '' : 's'}`
        return
      }
      if (m.type === 'roster_request') {
        names.set(m.requester, m.requester_name || 'Participant')
        await createPeer(m.requester, true)
        send({ type: 'peer_announce', target: m.requester })
        return
      }
      if (m.type === 'peer_announce') {
        names.set(m.peer_id, m.name || 'Participant')
        if (m.is_host) hostPeers.add(m.peer_id)
        await createPeer(m.peer_id, false)
        return
      }
      if (m.type === 'participant_left') {
        removePeer(m.peer_id)
        return
      }
      if (m.type === 'offer') {
        const pc = await createPeer(m.sender, false)
        if (!pc) return
        if (
          pc.signalingState !== 'stable' &&
          pc.signalingState !== 'have-remote-offer'
        )
          return
        await pc.setRemoteDescription(m.sdp)
        const answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        send({ type: 'answer', target: m.sender, sdp: pc.localDescription })
        return
      }
      if (m.type === 'answer') {
        const pc = peers.get(m.sender)
        if (pc && pc.signalingState === 'have-local-offer')
          await pc.setRemoteDescription(m.sdp)
        return
      }
      if (m.type === 'ice_candidate') {
        const pc = peers.get(m.sender)
        if (pc && m.candidate) {
          try {
            await pc.addIceCandidate(m.candidate)
          } catch {}
        }
        return
      }
      if (m.type === 'media_state') {
        const card = findCard(m.sender)
        if (card) {
          const label = card.querySelector('.peer-state')
          if (label)
            label.textContent =
              m.kind === 'audio' && !m.enabled
                ? 'Muted'
                : m.kind === 'video' && !m.enabled
                ? 'Camera off'
                : 'Connected'
          const v = card.querySelector('video')
          if (m.kind === 'video') v.style.opacity = m.enabled ? '1' : '.35'
        }
        return
      }
      if (m.type === 'MEETING_ENDED') {
        stopAll()
        location.href = window.VP_URLS.meetingEnded
      }
    }
  }

  async function start () {
    if (started) return
    started = true
    try {
      const r = await vpFetch(
        routeWithId(window.VP_URLS.meetingDetailTemplate, meetingId)
      )
      if (r.status === 401) {
        loginRedirect(`/meeting/${meetingId}/`)
        return
      }
      const info = await readApiResponse(r)
      if (!r.ok) throw new Error(info.detail || 'Meeting is unavailable.')
      if (info.access_state !== 'active' || !info.is_active) {
        status.textContent =
          info.access_message || 'Waiting for the meeting to start…'
        grid.innerHTML = `<div class="empty-state"><p>${escapeHtml(
          info.access_message || 'Waiting for the meeting to start…'
        )}</p></div>`
        if (info.access_state === 'waiting') {
          clearTimeout(waitingTimer)
          started = false
          waitingTimer = setTimeout(start, 5000)
        }
        return
      }
      isHost = !!info.is_host
      endBtn.classList.toggle('hidden', !isHost)
      recordBtn.classList.toggle('hidden', !isHost)
      recordingQuality
        .closest('.recording-select')
        ?.classList.toggle('hidden', !isHost)
      leaveBtn.classList.toggle('hidden', isHost)
      await getLocalMedia('saver')
      await loadRtcConfig()
      await connect()
    } catch (e) {
      status.textContent = e.message
      notify(e.message)
      started = false
    }
  }

  micBtn.onclick = () => {
    const t = localStream?.getAudioTracks()[0]
    if (!t) return
    t.enabled = !t.enabled
    micBtn.classList.toggle('active', t.enabled)
    micBtn.querySelector('span').textContent = t.enabled ? 'Mute' : 'Unmute'
    send({
      type: 'media_state',
      target: '*',
      kind: 'audio',
      enabled: t.enabled
    })
  }
  camBtn.onclick = () => {
    const t = localStream?.getVideoTracks()[0]
    if (!t) return
    t.enabled = !t.enabled
    camBtn.classList.toggle('active', t.enabled)
    camBtn.querySelector('span').textContent = t.enabled
      ? 'Camera'
      : 'Camera off'
    send({
      type: 'media_state',
      target: '*',
      kind: 'video',
      enabled: t.enabled
    })
  }
  recordingQuality.onchange = () => {
    if (recorder) {
      notify('Stop the recording before changing its resolution.')
      recordingQuality.value = recordingQuality.dataset.active || 'saver'
    }
  }
  quality.onchange = async () => {
    try {
      await getLocalMedia(quality.value)
      notify(
        `Call quality changed to ${quality.options[quality.selectedIndex].text}`
      )
    } catch {
      notify('This camera cannot provide that quality.')
      quality.value = 'saver'
    }
  }
  layoutBtn.onclick = () => {
    currentLayout = currentLayout === 'portrait' ? 'grid' : 'portrait'
    applyLayout()
    updateLayoutAvailability()
  }
  splitVerticalBtn.onclick = () => {
    if (participantCount() <= 3) {
      currentLayout =
        currentLayout === 'split-vertical' ? 'grid' : 'split-vertical'
      updateLayoutAvailability()
    }
  }
  splitSquareBtn.onclick = () => {
    if (participantCount() <= 3) {
      currentLayout = currentLayout === 'split-square' ? 'grid' : 'split-square'
      updateLayoutAvailability()
    }
  }
  copyBtn.onclick = async () => {
    try {
      await navigator.clipboard.writeText(location.href)
      notify('Invite copied.')
    } catch {
      notify('Copy is unavailable in this browser.')
    }
  }
  whatsappBtn.onclick = () =>
    window.open(
      `https://wa.me/?text=${encodeURIComponent(
        `Join my Videopods meeting: ${location.href}`
      )}`,
      '_blank',
      'noopener'
    )
  emailBtn.onclick = () =>
    (window.location.href = `mailto:?subject=${encodeURIComponent(
      'Join My Meeting'
    )}&body=${encodeURIComponent(location.href)}`)
  leaveBtn.onclick = () => {
    stopAll()
    location.href = window.VP_URLS.dashboard
  }
  endBtn.onclick = async () => {
    if (!isHost) return
    if (!confirm('End this meeting for everyone?')) return
    const r = await vpFetch(
      routeWithId(window.VP_URLS.meetingEndTemplate, meetingId),
      { method: 'POST' }
    )
    if (r.ok) {
      stopAll()
      location.href = window.VP_URLS.meetingEnded
    } else notify('Only the host can end this meeting.')
  }
  recordBtn.onclick = () => (recorder ? stopRecording() : startRecording())

  async function openDb () {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(`videopods-${meetingId}`, 1)
      req.onupgradeneeded = () =>
        req.result.createObjectStore('chunks', { keyPath: 'sequence' })
      req.onsuccess = () => resolve(req.result)
      req.onerror = () => reject(req.error)
    })
  }
  async function storeChunk (blob) {
    const db = await openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction('chunks', 'readwrite')
      tx.objectStore('chunks').put({
        sequence: chunkSequence++,
        blob,
        timestamp: Date.now()
      })
      tx.oncomplete = resolve
      tx.onerror = () => reject(tx.error)
    })
  }
  async function readChunks () {
    const db = await openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction('chunks', 'readonly')
      const req = tx.objectStore('chunks').getAll()
      req.onsuccess = () =>
        resolve(
          req.result.sort((a, b) => a.sequence - b.sequence).map(x => x.blob)
        )
      req.onerror = () => reject(req.error)
    })
  }
  async function clearChunks () {
    const db = await openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction('chunks', 'readwrite')
      tx.objectStore('chunks').clear()
      tx.oncomplete = resolve
      tx.onerror = () => reject(tx.error)
    })
  }

  function drawCover (context, video, x, y, width, height) {
    if (video.readyState < 2 || !video.videoWidth || !video.videoHeight) return
    const scale = Math.max(
        width / video.videoWidth,
        height / video.videoHeight
      ),
      sw = width / scale,
      sh = height / scale,
      sx = (video.videoWidth - sw) / 2,
      sy = (video.videoHeight - sh) / 2
    context.drawImage(video, sx, sy, sw, sh, x, y, width, height)
  }
  function recordingSource () {
    const preset = RECORDING[recordingQuality.value] || RECORDING.saver
    const count = Math.max(1, participantCount())
    const splitVertical = currentLayout === 'split-vertical' && count <= 3
    const splitSquare = currentLayout === 'split-square' && count <= 3
    const portrait = currentLayout === 'portrait'
    const canvas = document.createElement('canvas')
    if (splitVertical) {
      canvas.width = Math.min(preset.width, preset.height)
      canvas.height = Math.max(preset.width, preset.height)
    } else if (splitSquare) {
      const s = Math.min(preset.width, preset.height)
      canvas.width = s
      canvas.height = s
    } else if (portrait) {
      const cardW = Math.max(1, Math.round((preset.height * 9) / 16))
      const cols = count <= 3 ? count : 2
      const rows = Math.ceil(count / cols)
      canvas.width = cardW * cols
      canvas.height = Math.min(preset.height * 2, preset.height * rows)
    } else {
      canvas.width = preset.width
      canvas.height = preset.height
    }
    const ctx = canvas.getContext('2d', { alpha: false })
    let frame = 0
    const draw = () => {
      const videos = [...grid.querySelectorAll('video')]
      ctx.fillStyle = '#0b1220'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      if (splitVertical) {
        const h = canvas.height / Math.max(1, videos.length)
        videos.forEach((v, i) => drawCover(ctx, v, 0, i * h, canvas.width, h))
      } else if (splitSquare) {
        const w = canvas.width / Math.max(1, videos.length)
        videos.forEach((v, i) => drawCover(ctx, v, i * w, 0, w, canvas.height))
      } else if (portrait && videos.length) {
        const cols = videos.length <= 3 ? videos.length : 2,
          rows = Math.ceil(videos.length / cols),
          cardW = canvas.width / cols,
          cardH = canvas.height / rows
        videos.forEach((v, i) =>
          drawCover(
            ctx,
            v,
            (i % cols) * cardW,
            Math.floor(i / cols) * cardH,
            cardW,
            cardH
          )
        )
      } else if (videos.length) {
        const cols =
            videos.length <= 1
              ? 1
              : videos.length <= 4
              ? 2
              : Math.ceil(Math.sqrt(videos.length)),
          rows = Math.ceil(videos.length / cols),
          w = canvas.width / cols,
          h = canvas.height / rows
        videos.forEach((v, i) =>
          drawCover(ctx, v, (i % cols) * w, Math.floor(i / cols) * h, w, h)
        )
      }
      frame = requestAnimationFrame(draw)
    }
    draw()
    return {
      stream: canvas.captureStream(preset.fps),
      stop: () => cancelAnimationFrame(frame)
    }
  }
  async function startRecording () {
    if (!isHost || recorder) return
    try {
      recordingWanted = true
      recordingQuality.dataset.active = recordingQuality.value
      recorderStream = recordingSource()
      const preset = RECORDING[recordingQuality.value] || RECORDING.saver
      const audio = localStream?.getAudioTracks()[0]
      if (audio) recorderStream.stream.addTrack(audio)
      const mime = MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus')
        ? 'video/webm;codecs=vp8,opus'
        : 'video/webm'
      recorder = new MediaRecorder(recorderStream.stream, {
        mimeType: mime,
        videoBitsPerSecond: preset.bitrate,
        audioBitsPerSecond: 64000
      })
      chunkSequence = 0
      pendingChunkWrites.clear()
      recorder.ondataavailable = e => {
        if (e.data?.size) {
          const write = storeChunk(e.data).finally(() =>
            pendingChunkWrites.delete(write)
          )
          pendingChunkWrites.add(write)
        }
      }
      recorder.onstop = async () => {
        await Promise.allSettled([...pendingChunkWrites])
        if (recordingWanted) {
          recorderStream?.stop()
          recorder = null
          setTimeout(() => startRecording(), 250)
          return
        }
        try {
          const blobs = await readChunks()
          if (blobs.length) {
            const url = URL.createObjectURL(new Blob(blobs, { type: mime })),
              a = document.createElement('a')
            a.href = url
            a.download = `videopods-${meetingId}.webm`
            a.click()
            setTimeout(() => URL.revokeObjectURL(url), 1000)
            await clearChunks()
          }
        } finally {
          recorderStream?.stop()
          recorder = null
          recordBtn.querySelector('span').textContent = 'Record'
          recordBtn.classList.remove('active')
        }
      }
      recorder.start(5000)
      recordBtn.classList.add('active')
      recordBtn.querySelector('span').textContent = 'Stop'
      notify(
        `Local recording started · ${
          recordingQuality.options[recordingQuality.selectedIndex].text
        }`
      )
    } catch {
      recordingWanted = false
      recorderStream?.stop()
      recorderStream = null
      recorder = null
      notify('Recording could not start in this browser.')
    }
  }
  function stopRecording () {
    recordingWanted = false
    if (recorder && recorder.state !== 'inactive') recorder.stop()
  }
  function stopAll () {
    stopping = true
    clearTimeout(waitingTimer)
    try {
      stopRecording()
    } catch {}
    socket?.close()
    peers.forEach(pc => {
      try {
        pc.close()
      } catch {}
    })
    peers.clear()
    localStream?.getTracks().forEach(t => t.stop())
  }

  // I intentionally do not end a host meeting on pagehide; refreshing or closing a tab must not terminate the meeting.
  window.addEventListener('pagehide', () => {
    try {
      socket?.close()
    } catch {}
  })
  start()
})()
