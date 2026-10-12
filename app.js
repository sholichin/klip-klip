// KLIP KLIP — Main Application Logic

let currentVideoMetadata = null;
let currentClips = [];
let activeClip = null;
let currentSettings = {
  gemini_api_key: '',
  gemini_model: 'gemini-1.5-flash',
  default_layout: 'blurred_bg',
  default_hook_style: 'badge_yellow',
  default_subtitle_style: 'karaoke_yellow'
};

document.addEventListener('DOMContentLoaded', async () => {
  PhonePreview.init();
  await loadSettings();
  setupEventListeners();
});

// Load settings from backend
async function loadSettings() {
  try {
    const res = await fetch('/api/settings');
    if (res.ok) {
      const data = await res.json();
      currentSettings = { ...currentSettings, ...data };
      updateGeminiStatusBadge(data.has_gemini_key);
      if (document.getElementById('inputGeminiApiKey') && data.gemini_api_key_masked) {
        document.getElementById('inputGeminiApiKey').placeholder = data.gemini_api_key_masked;
      }
      if (document.getElementById('selectGeminiModel')) {
        document.getElementById('selectGeminiModel').value = data.gemini_model || 'gemini-1.5-flash';
      }
    }
  } catch (err) {
    console.error('Error loading settings:', err);
  }
}

function updateGeminiStatusBadge(hasKey) {
  const badge = document.getElementById('statusGemini');
  const text = document.getElementById('geminiStatusText');
  if (hasKey) {
    badge.className = 'flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs bg-emerald-500/10 border border-emerald-500/30 text-emerald-400';
    text.textContent = 'Gemini AI Aktif';
  } else {
    badge.className = 'flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs bg-amber-500/10 border border-amber-500/30 text-amber-400';
    text.textContent = 'Mode Heuristik (Tanpa Key)';
  }
}

function setupEventListeners() {
  // Sample URLs
  document.querySelectorAll('.btn-sample').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const url = e.currentTarget.getAttribute('data-url');
      document.getElementById('inputYoutubeUrl').value = url;
      startAnalysis(url);
    });
  });

  // Analyze button
  document.getElementById('btnAnalyze').addEventListener('click', () => {
    const url = document.getElementById('inputYoutubeUrl').value.trim();
    if (!url) {
      alert('Silakan masukkan tautan video YouTube terlebih dahulu!');
      return;
    }
    startAnalysis(url);
  });

  // Enter key on URL input
  document.getElementById('inputYoutubeUrl').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      document.getElementById('btnAnalyze').click();
    }
  });

  // Live Hook text input
  document.getElementById('editHookText').addEventListener('input', (e) => {
    const val = e.target.value;
    if (activeClip) {
      activeClip.hook_text = val.toUpperCase();
    }
    PhonePreview.setHookText(val);
  });

  // Layout Selector
  document.getElementById('btnLayoutBlur').addEventListener('click', () => {
    setLayoutMode('blurred_bg');
  });
  document.getElementById('btnLayoutCrop').addEventListener('click', () => {
    setLayoutMode('crop_center');
  });

  // Toggle Show Hook Banner
  const toggleHook = document.getElementById('toggleShowHook');
  if (toggleHook) {
    toggleHook.addEventListener('change', (e) => {
      const isChecked = e.target.checked;
      PhonePreview.setShowHook(isChecked);
      if (activeClip) activeClip.show_hook = isChecked;
      const group = document.getElementById('hookTextInputGroup');
      if (group) group.style.opacity = isChecked ? '1' : '0.4';
    });
  }

  // Speaker Focus Preset Buttons (Left, Center, Right, Split)
  document.querySelectorAll('.btn-speaker').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const spk = e.currentTarget.getAttribute('data-speaker');
      document.querySelectorAll('.btn-speaker').forEach(b => {
        b.className = 'btn-speaker px-2 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-center transition';
      });
      e.currentTarget.className = 'btn-speaker px-2 py-1.5 rounded-xl bg-amber-500/20 text-amber-300 border border-amber-400 text-center transition';
      
      let percent = 50;
      let label = 'Tengah (50%)';
      if (spk === 'left') { percent = 20; label = 'Kiri (20%)'; }
      else if (spk === 'right') { percent = 80; label = 'Kanan (80%)'; }
      else if (spk === 'split') { label = 'Split 2 Orang'; }

      document.getElementById('sliderSpeakerFocus').value = percent;
      document.getElementById('speakerPositionLabel').textContent = label;

      if (activeClip) activeClip.speaker_focus = spk;
      PhonePreview.setSpeakerFocus(spk, percent);

      // Otomatis aktifkan layout Speaker Crop jika memilih arah pembicara
      if (spk === 'split') {
        setLayoutMode('split');
      } else if (PhonePreview.currentLayout !== 'crop_center') {
        setLayoutMode('crop_center');
      }
    });
  });

  // Speaker Focus Slider
  const speakerSlider = document.getElementById('sliderSpeakerFocus');
  if (speakerSlider) {
    speakerSlider.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      document.getElementById('speakerPositionLabel').textContent = `Kustom (${val}%)`;
      document.querySelectorAll('.btn-speaker').forEach(b => {
        b.className = 'btn-speaker px-2 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-center transition';
      });

      const frac = (val / 100).toFixed(2);
      if (activeClip) activeClip.speaker_focus = frac;
      PhonePreview.setSpeakerFocus(frac, val);

      if (PhonePreview.currentLayout !== 'crop_center') {
        setLayoutMode('crop_center');
      }
    });
  }

  // Hook Style Buttons
  document.querySelectorAll('.btn-hook-style').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const style = e.currentTarget.getAttribute('data-style');
      document.querySelectorAll('.btn-hook-style').forEach(b => b.classList.remove('ring-2', 'ring-white'));
      e.currentTarget.classList.add('ring-2', 'ring-white');
      PhonePreview.setHookStyle(style);
      if (activeClip) activeClip.hook_style = style;
    });
  });

  // Subtitle Style Buttons
  document.querySelectorAll('.btn-sub-style').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const subStyle = e.currentTarget.getAttribute('data-sub');
      document.querySelectorAll('.btn-sub-style').forEach(b => b.classList.remove('border-amber-400', 'border-emerald-400', 'border-cyan-400'));
      if (subStyle === 'karaoke_yellow') e.currentTarget.classList.add('border-amber-400');
      if (subStyle === 'karaoke_green') e.currentTarget.classList.add('border-emerald-400');
      if (subStyle === 'karaoke_cyan') e.currentTarget.classList.add('border-cyan-400');
      PhonePreview.setSubtitleStyle(subStyle);
      if (activeClip) activeClip.subtitle_style = subStyle;
    });
  });

  // Render Clip Button
  document.getElementById('btnRenderClip').addEventListener('click', handleRenderClip);

  // Settings Modal controls
  document.getElementById('btnOpenSettings').addEventListener('click', () => {
    document.getElementById('settingsModal').classList.remove('hidden');
  });
  document.getElementById('btnCloseSettingsModal').addEventListener('click', () => {
    document.getElementById('settingsModal').classList.add('hidden');
  });
  document.getElementById('btnSaveSettings').addEventListener('click', handleSaveSettings);

  // Export Modal Close
  document.getElementById('btnCloseExportModal').addEventListener('click', () => {
    const player = document.getElementById('modalVideoPlayer');
    if (player) player.pause();
    document.getElementById('exportModal').classList.add('hidden');
  });

  // 1-Click Copy Buttons
  document.querySelectorAll('.btn-copy').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const targetId = e.currentTarget.getAttribute('data-target');
      const text = document.getElementById(targetId)?.innerText;
      if (text) {
        navigator.clipboard.writeText(text);
        const originalText = e.currentTarget.innerText;
        e.currentTarget.innerText = 'Tersalin! ✓';
        e.currentTarget.classList.add('text-emerald-400');
        setTimeout(() => {
          e.currentTarget.innerText = originalText;
          e.currentTarget.classList.remove('text-emerald-400');
        }, 2000);
      }
    });
  });
}

function setLayoutMode(mode) {
  const btnBlur = document.getElementById('btnLayoutBlur');
  const btnCrop = document.getElementById('btnLayoutCrop');

  if (mode === 'blurred_bg') {
    btnBlur.className = 'btn-layout px-3 py-2 rounded-xl text-xs font-bold bg-amber-500/20 border border-amber-400 text-amber-300 flex items-center justify-center space-x-1.5';
    btnCrop.className = 'btn-layout px-3 py-2 rounded-xl text-xs font-bold bg-slate-800 border border-slate-700 text-slate-400 hover:text-slate-200 flex items-center justify-center space-x-1.5';
  } else {
    btnCrop.className = 'btn-layout px-3 py-2 rounded-xl text-xs font-bold bg-amber-500/20 border border-amber-400 text-amber-300 flex items-center justify-center space-x-1.5';
    btnBlur.className = 'btn-layout px-3 py-2 rounded-xl text-xs font-bold bg-slate-800 border border-slate-700 text-slate-400 hover:text-slate-200 flex items-center justify-center space-x-1.5';
  }
  PhonePreview.setLayout(mode);
  if (activeClip) activeClip.layout = mode;
}

// Start Video Analysis
async function startAnalysis(url) {
  const overlay = document.getElementById('loadingOverlay');
  overlay.classList.remove('hidden');

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Gagal menganalisis video.');
    }

    currentVideoMetadata = data.metadata;
    currentClips = data.clips;

    // Display metadata bar
    renderMetadataBar(data.metadata, data.clips.length);

    // Display clips feed
    renderClipsFeed(data.clips);

    // Show sections
    document.getElementById('metadataSection').classList.remove('hidden');
    document.getElementById('studioSection').classList.remove('hidden');

    // Select first clip automatically
    if (data.clips && data.clips.length > 0) {
      selectClip(data.clips[0], 0);
    }

    // Scroll smoothly to studio
    document.getElementById('metadataSection').scrollIntoView({ behavior: 'smooth' });

  } catch (err) {
    alert('Terjadi kesalahan: ' + err.message);
  } finally {
    overlay.classList.add('hidden');
  }
}

function renderMetadataBar(meta, clipCount) {
  document.getElementById('metaThumb').src = meta.thumbnail;
  document.getElementById('metaTitle').textContent = meta.title;
  document.getElementById('metaChannel').textContent = meta.channel;
  
  const minutes = Math.floor(meta.duration / 60);
  const seconds = meta.duration % 60;
  document.getElementById('metaDuration').textContent = `⏱ ${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
  document.getElementById('metaClipCount').textContent = `${clipCount} Klip Viral`;

  // Set initial preview thumbnail
  PhonePreview.setThumbnail(meta.thumbnail);
}

function renderClipsFeed(clips) {
  const container = document.getElementById('clipsFeedContainer');
  container.innerHTML = '';

  if (!clips || clips.length === 0) {
    container.innerHTML = '<div class="p-6 text-center text-slate-400 bg-slate-900 rounded-2xl border border-slate-800">Tidak ada klip yang terdeteksi. Silakan coba video lain.</div>';
    return;
  }

  clips.forEach((clip, idx) => {
    const card = document.createElement('div');
    card.className = `clip-card p-5 rounded-2xl border transition cursor-pointer ${idx === 0 ? 'bg-[#18233A] border-amber-400/80 shadow-lg shadow-amber-500/10' : 'bg-[#12192A] border-[#243452] hover:border-slate-600'}`;
    card.setAttribute('data-clip-index', idx);

    // Format Start & End timestamp
    const startM = Math.floor(clip.start_time / 60);
    const startS = Math.floor(clip.start_time % 60);
    const endM = Math.floor(clip.end_time / 60);
    const endS = Math.floor(clip.end_time % 60);
    const timeStr = `${startM}:${startS < 10 ? '0' : ''}${startS} - ${endM}:${endS < 10 ? '0' : ''}${endS} (${clip.duration}s)`;

    // Virality score badge
    const v = clip.virality || { score: 85, grade: 'A', badge_color: 'emerald' };
    let badgeBg = 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
    if (v.score < 80) badgeBg = 'bg-amber-500/20 text-amber-400 border-amber-500/40';

    card.innerHTML = `
      <div class="flex items-start justify-between gap-3 mb-2">
        <div class="flex items-center space-x-2">
          <span class="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-black text-amber-400">
            #${idx + 1}
          </span>
          <h4 class="font-bold text-sm text-slate-100">${clip.title}</h4>
        </div>
        <div class="flex-shrink-0 px-2.5 py-0.5 rounded-full text-[11px] font-extrabold border ${badgeBg}">
          Virality: ${v.score}/100
        </div>
      </div>

      <!-- Hook Box -->
      <div class="my-2.5 p-3 rounded-xl bg-[#090D18] border border-amber-500/30 flex items-center space-x-2">
        <span class="text-amber-400 font-extrabold text-xs">HOOK:</span>
        <span class="text-xs font-bold text-amber-200 uppercase tracking-tight truncate">${clip.hook_text}</span>
      </div>

      <p class="text-xs text-slate-400 line-clamp-2 mb-3">
        💡 <strong class="text-slate-300">Kenapa Viral:</strong> ${clip.virality_reason}
      </p>

      <div class="flex items-center justify-between pt-2 border-t border-slate-800/80 text-[11px] text-slate-400">
        <div class="flex items-center space-x-2">
          <span class="px-2 py-0.5 rounded bg-slate-800 font-mono text-slate-300">⏱ ${timeStr}</span>
          <span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-bold">✓ MotionKlip Ready</span>
        </div>
        <button class="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500 text-amber-300 hover:text-black font-extrabold text-xs transition">
          Pilih & Edit &rarr;
        </button>
      </div>
    `;

    card.addEventListener('click', () => {
      document.querySelectorAll('.clip-card').forEach(c => {
        c.className = 'clip-card p-5 rounded-2xl border transition cursor-pointer bg-[#12192A] border-[#243452] hover:border-slate-600';
      });
      card.className = 'clip-card p-5 rounded-2xl border transition cursor-pointer bg-[#18233A] border-amber-400/80 shadow-lg shadow-amber-500/10';
      selectClip(clip, idx);
    });

    container.appendChild(card);
  });

  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function selectClip(clip, index) {
  activeClip = { ...clip };
  activeClip.layout = activeClip.layout || 'blurred_bg';
  activeClip.speaker_focus = activeClip.speaker_focus || 'center';
  activeClip.show_hook = activeClip.show_hook !== undefined ? activeClip.show_hook : true;
  activeClip.hook_style = activeClip.hook_style || 'badge_yellow';
  activeClip.subtitle_style = activeClip.subtitle_style || 'karaoke_yellow';

  // Update simulator indicator
  document.getElementById('activeClipIndicator').textContent = `Klip #${index + 1}`;
  
  // Update inputs
  document.getElementById('editHookText').value = clip.hook_text;
  const toggleHook = document.getElementById('toggleShowHook');
  if (toggleHook) toggleHook.checked = activeClip.show_hook;
  const hookGroup = document.getElementById('hookTextInputGroup');
  if (hookGroup) hookGroup.style.opacity = activeClip.show_hook ? '1' : '0.4';
  
  // Update Simulator
  PhonePreview.setShowHook(activeClip.show_hook);
  PhonePreview.setHookText(clip.hook_text);
  PhonePreview.setHookStyle(activeClip.hook_style);
  PhonePreview.setLayout(activeClip.layout);
  PhonePreview.setSubtitleStyle(activeClip.subtitle_style);

  // Set sample dialogue snippet in simulator
  const words = (clip.transcript_snippet || "RAHASIA INI AKHIRNYA TERBONGKAR").split(" ");
  if (words.length > 2) {
    PhonePreview.setSubtitleText(words.slice(0, -1).join(" ").toUpperCase(), words[words.length - 1].toUpperCase());
  }
}

// Render Clip Process
async function handleRenderClip() {
  if (!activeClip || !currentVideoMetadata) {
    alert('Pilih klip terlebih dahulu!');
    return;
  }

  const btn = document.getElementById('btnRenderClip');
  const originalHTML = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `
    <div class="w-5 h-5 border-2 border-black border-t-transparent rounded-full animate-spin"></div>
    <span>Rendering Video Kilat VideoToolbox...</span>
  `;

  try {
    const isShowHook = document.getElementById('toggleShowHook') ? document.getElementById('toggleShowHook').checked : true;
    const payload = {
      url: currentVideoMetadata.url,
      clip_id: activeClip.clip_id,
      start_time: activeClip.start_time,
      end_time: activeClip.end_time,
      hook_text: document.getElementById('editHookText').value || activeClip.hook_text,
      hook_style: activeClip.hook_style || 'badge_yellow',
      layout: activeClip.layout || 'blurred_bg',
      speaker_focus: activeClip.speaker_focus || 'center',
      show_hook: isShowHook,
      subtitle_style: activeClip.subtitle_style || 'karaoke_yellow',
      font_size: 58
    };

    const res = await fetch('/api/render', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Gagal merender video.');
    }

    // Populate Export & Monetization Modal
    document.getElementById('btnDownloadVideo').href = data.download_url;
    document.getElementById('btnDownloadVideo').setAttribute('download', data.filename);
    
    // Set Video Player Preview
    const videoPlayer = document.getElementById('modalVideoPlayer');
    if (videoPlayer) {
      videoPlayer.src = data.download_url;
      videoPlayer.load();
    }
    
    // Set 1-Click Copy Data
    const social = activeClip.social || {};
    document.getElementById('copyTitleText').textContent = payload.hook_text;
    document.getElementById('copyCaptionText').textContent = social.caption_tiktok || payload.hook_text;
    document.getElementById('copyRewardText').textContent = social.caption_motionklip || `[KLIP KLIP REWARD] ${payload.hook_text}\n#motionklip #klipreward`;

    // Open Modal
    document.getElementById('exportModal').classList.remove('hidden');

  } catch (err) {
    alert('Terjadi kesalahan saat render: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHTML;
  }
}

// Save Settings
async function handleSaveSettings() {
  const key = document.getElementById('inputGeminiApiKey').value.trim();
  const model = document.getElementById('selectGeminiModel').value;

  const payload = { gemini_model: model };
  if (key) payload.gemini_api_key = key;

  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      alert('Pengaturan berhasil disimpan!');
      document.getElementById('settingsModal').classList.add('hidden');
      await loadSettings();
    }
  } catch (err) {
    alert('Gagal menyimpan pengaturan: ' + err.message);
  }
}
