// KLIP KLIP — 9:16 Smartphone Simulator Controller

const PhonePreview = {
  currentLayout: 'blurred_bg',
  currentHookStyle: 'badge_yellow',
  currentSubStyle: 'karaoke_yellow',
  currentSpeakerFocus: 'center',
  currentSpeakerPercent: 50,
  showHook: true,

  init() {
    this.simBg = document.getElementById('simBgImage');
    this.simFg = document.getElementById('simFgImage');
    this.simHookBanner = document.getElementById('simHookBanner');
    this.simHookText = document.getElementById('simHookText');
    this.simSubtitle = document.getElementById('simSubtitle');
    this.simSubLine = document.getElementById('simSubLine');
  },

  setThumbnail(thumbUrl) {
    if (this.simBg && this.simFg) {
      this.simBg.src = thumbUrl;
      this.simFg.src = thumbUrl;
    }
  },

  setHookText(text) {
    if (this.simHookText) {
      this.simHookText.textContent = text.toUpperCase() || 'JANGAN LAKUKAN INI SEBELUM TERLAMBAT! 😱';
    }
  },

  setShowHook(show) {
    this.showHook = show;
    if (this.simHookBanner) {
      this.simHookBanner.style.display = show ? 'block' : 'none';
    }
  },

  setHookStyle(styleName) {
    this.currentHookStyle = styleName;
    if (this.simHookBanner) {
      this.simHookBanner.className = `sim-hook-banner ${styleName}`;
    }
  },

  setLayout(layoutType) {
    this.currentLayout = layoutType;
    if (!this.simBg || !this.simFg) return;

    if (layoutType === 'crop_center') {
      this.simBg.style.display = 'none';
      this.simFg.className = 'preview-fg-crop';
      this.simFg.style.objectPosition = `${this.currentSpeakerPercent}% center`;
    } else {
      // blurred_bg
      this.simBg.style.display = 'block';
      this.simBg.className = 'preview-bg-blur';
      this.simFg.className = 'preview-fg-center';
      this.simFg.style.objectPosition = 'center center';
    }
  },

  setSpeakerFocus(focus, percent) {
    this.currentSpeakerFocus = focus;
    this.currentSpeakerPercent = percent;

    if (this.currentLayout === 'crop_center' && this.simFg) {
      this.simFg.style.objectPosition = `${percent}% center`;
    }
  },

  setSubtitleStyle(subStyle) {
    this.currentSubStyle = subStyle;
    if (!this.simSubtitle) return;
    
    this.simSubtitle.className = 'sim-subtitle';
    if (subStyle === 'karaoke_green') {
      this.simSubtitle.classList.add('green');
    } else if (subStyle === 'karaoke_cyan') {
      this.simSubtitle.classList.add('cyan');
    }
  },

  setSubtitleText(mainWords, highlightWord) {
    if (this.simSubLine) {
      this.simSubLine.innerHTML = `${mainWords} <span class="highlight">${highlightWord}</span>`;
    }
  }
};

window.PhonePreview = PhonePreview;
