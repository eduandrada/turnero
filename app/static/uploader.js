/**
 * ==============================================================================
 * BLADESYNC 2026 - COMPONENTE UNIVERSAL DE SUBIDA DE IMÁGENES (UI/UX)
 * Soporta Drag & Drop, Previsualización Instantánea, Barra de Progreso y WebP Pipeline.
 * ==============================================================================
 */

class UniversalImageUploader {
  /**
   * @param {Object} options
   * @param {HTMLElement|string} options.container - Contenedor DOM donde se renderizará el componente
   * @param {'avatar'|'product'|'branding'} options.context - Contexto de la imagen
   * @param {string|null} [options.currentImageUrl] - URL de imagen existente previa (si edita)
   * @param {Function} [options.onUploadSuccess] - Callback al subir exitosamente (data) => {}
   * @param {Function} [options.onUploadError] - Callback de error (errorMsg) => {}
   * @param {Function} [options.onImageRemoved] - Callback al quitar imagen () => {}
   */
  constructor(options) {
    this.container = typeof options.container === "string" 
      ? document.querySelector(options.container) 
      : options.container;
    this.context = options.context || "product";
    this.currentImageUrl = options.currentImageUrl || null;
    this.onUploadSuccess = options.onUploadSuccess || (() => {});
    this.onUploadError = options.onUploadError || (() => {});
    this.onImageRemoved = options.onImageRemoved || (() => {});
    
    this.selectedFile = null;
    this.uploadedUrl = this.currentImageUrl;
    this.isUploading = false;

    this.init();
  }

  init() {
    if (!this.container) return;
    this.render();
    this.bindEvents();
  }

  render() {
    const hasExisting = Boolean(this.uploadedUrl);
    const idSuffix = Math.random().toString(36).substring(2, 9);
    this.inputId = `uploader_file_${idSuffix}`;

    this.container.innerHTML = `
      <div class="universal-uploader-box border-2 border-dashed border-[#23232c] hover:border-[#d4ff00]/60 rounded-2xl p-4 bg-[#131318]/70 text-center transition-all duration-200 relative group flex flex-col items-center justify-center min-h-[160px] overflow-hidden">
        
        <!-- INPUT OCULTO -->
        <input type="file" id="${this.inputId}" accept=".jpg,.jpeg,.png,.webp" class="hidden" />

        <!-- ESTADO INICIAL / DROPZONE -->
        <div class="uploader-idle-zone flex flex-col items-center gap-2 cursor-pointer w-full py-2 ${hasExisting ? 'hidden' : ''}">
          <div class="w-12 h-12 rounded-2xl bg-[#1a1a22] border border-[#23232c] flex items-center justify-center text-xl text-[#d4ff00] group-hover:scale-110 transition shadow-inner">
            📷
          </div>
          <div class="flex flex-col items-center">
            <span class="text-xs font-mono font-bold text-white group-hover:text-[#d4ff00] transition">
              Seleccionar o arrastrar imagen
            </span>
            <span class="text-[10px] text-gray-500 font-mono mt-0.5">
              JPG, PNG o WebP (Máx. 5 MB) · Optimizado a WebP
            </span>
          </div>
          <button type="button" class="mt-1 px-3 py-1.5 rounded-full bg-[#1a1a22] border border-[#23232c] hover:border-[#d4ff00] text-[11px] font-mono text-gray-300 hover:text-white transition flex items-center gap-1.5 shadow-sm">
            <span>📷 Seleccionar archivo</span>
          </button>
        </div>

        <!-- PREVIEW ACTIVO -->
        <div class="uploader-preview-zone flex flex-col items-center gap-2.5 w-full ${hasExisting ? '' : 'hidden'}">
          <div class="relative rounded-xl overflow-hidden border border-[#23232c] bg-black/40 shadow-lg max-h-48 max-w-full">
            <img src="${this.uploadedUrl || ''}" alt="Previsualización" class="uploader-img-preview object-contain max-h-40 rounded-lg transition" />
            <div class="absolute inset-0 bg-black/50 opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
              <button type="button" class="btn-change-image px-2.5 py-1 rounded bg-[#1a1a22] border border-[#23232c] text-xs font-mono text-white hover:text-[#d4ff00] transition shadow">
                🔄 Cambiar
              </button>
              <button type="button" class="btn-remove-image px-2.5 py-1 rounded bg-red-950/80 border border-red-500/40 text-xs font-mono text-red-300 hover:text-white transition shadow">
                🗑️ Quitar
              </button>
            </div>
          </div>
          <div class="uploader-file-info text-[11px] font-mono text-gray-400 truncate max-w-xs">
            ${hasExisting ? 'Imagen actual vinculada' : ''}
          </div>
        </div>

        <!-- BARRA DE PROGRESO Y SPINNER -->
        <div class="uploader-progress-zone hidden flex-col items-center gap-2 w-full py-4">
          <div class="flex items-center justify-between w-full max-w-xs text-[11px] font-mono text-gray-300">
            <span class="flex items-center gap-1.5 text-[#d4ff00]">
              <span class="animate-spin inline-block">⚙️</span> Procesando en servidor...
            </span>
            <span class="uploader-percent font-bold text-white">0%</span>
          </div>
          <div class="w-full max-w-xs h-2 bg-[#1a1a22] rounded-full overflow-hidden border border-[#23232c]">
            <div class="uploader-progress-bar h-full bg-gradient-to-r from-[#d4ff00] to-emerald-400 w-0 transition-all duration-150"></div>
          </div>
          <span class="text-[10px] text-gray-500 font-mono">Comprimiendo y optimizando a WebP...</span>
        </div>

      </div>
    `;

    this.fileInput = this.container.querySelector(`#${this.inputId}`);
    this.idleZone = this.container.querySelector('.uploader-idle-zone');
    this.previewZone = this.container.querySelector('.uploader-preview-zone');
    this.imgPreview = this.container.querySelector('.uploader-img-preview');
    this.fileInfo = this.container.querySelector('.uploader-file-info');
    this.progressZone = this.container.querySelector('.uploader-progress-zone');
    this.progressBar = this.container.querySelector('.uploader-progress-bar');
    this.percentText = this.container.querySelector('.uploader-percent');
    this.box = this.container.querySelector('.universal-uploader-box');
  }

  bindEvents() {
    if (!this.fileInput || !this.box) return;

    // Click en la zona inactiva abre selector de archivo
    this.idleZone.addEventListener('click', () => this.fileInput.click());

    // Botón cambiar
    const btnChange = this.container.querySelector('.btn-change-image');
    if (btnChange) {
      btnChange.addEventListener('click', (e) => {
        e.stopPropagation();
        this.fileInput.click();
      });
    }

    // Botón quitar
    const btnRemove = this.container.querySelector('.btn-remove-image');
    if (btnRemove) {
      btnRemove.addEventListener('click', (e) => {
        e.stopPropagation();
        this.clear();
      });
    }

    // Cambio en input
    this.fileInput.addEventListener('change', (e) => {
      const file = e.target.files?.[0];
      if (file) this.handleFileSelected(file);
    });

    // Drag & Drop
    ['dragenter', 'dragover'].forEach(eventName => {
      this.box.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.box.classList.add('border-[#d4ff00]', 'bg-[#1a1a24]');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      this.box.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.box.classList.remove('border-[#d4ff00]', 'bg-[#1a1a24]');
      }, false);
    });

    this.box.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const file = dt?.files?.[0];
      if (file) this.handleFileSelected(file);
    });
  }

  handleFileSelected(file) {
    // Validar tipo básico
    const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg'];
    if (!validTypes.includes(file.type.toLowerCase()) && !file.name.match(/\.(jpg|jpeg|png|webp)$/i)) {
      alert("Por favor seleccione un archivo JPG, PNG o WebP válido.");
      return;
    }

    // Validar tamaño máximo 5MB
    if (file.size > 5 * 1024 * 1024) {
      alert(`El archivo seleccionado (${(file.size / (1024 * 1024)).toFixed(2)} MB) supera el límite máximo de 5 MB.`);
      return;
    }

    this.selectedFile = file;

    // Previsualización instantánea en cliente
    const objectUrl = URL.createObjectURL(file);
    this.imgPreview.src = objectUrl;
    this.fileInfo.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;

    this.idleZone.classList.add('hidden');
    this.previewZone.classList.remove('hidden');

    // Disparar subida automática
    this.upload();
  }

  async upload() {
    if (!this.selectedFile || this.isUploading) return;

    this.isUploading = true;
    this.previewZone.classList.add('hidden');
    this.progressZone.classList.remove('hidden');
    this.progressBar.style.width = '10%';
    this.percentText.textContent = '10%';

    const formData = new FormData();
    formData.append("file", this.selectedFile);
    formData.append("context", this.context);
    if (this.currentImageUrl) {
      formData.append("previous_url", this.currentImageUrl);
    }

    const token = localStorage.getItem("bladesync_admin_token");

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/media/upload");

      if (token) {
        xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      }

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          const percent = Math.min(95, Math.round((e.loaded / e.total) * 100));
          this.progressBar.style.width = `${percent}%`;
          this.percentText.textContent = `${percent}%`;
        }
      };

      xhr.onload = () => {
        this.isUploading = false;
        this.progressZone.classList.add('hidden');

        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText);
            this.uploadedUrl = data.url;
            this.currentImageUrl = data.url;
            this.imgPreview.src = data.url;
            this.fileInfo.textContent = `Guardado: ${data.filename} (${data.width}x${data.height} px, WebP)`;
            this.previewZone.classList.remove('hidden');
            this.onUploadSuccess(data);
            resolve(data);
          } catch (e) {
            this.handleUploadFailure("Respuesta no válida del servidor.");
            reject(e);
          }
        } else {
          let errDetail = "Error al subir la imagen.";
          try {
            const errJson = JSON.parse(xhr.responseText);
            errDetail = errJson.detail || errDetail;
          } catch (_) {}
          this.handleUploadFailure(errDetail);
          reject(new Error(errDetail));
        }
      };

      xhr.onerror = () => {
        this.isUploading = false;
        this.progressZone.classList.add('hidden');
        this.handleUploadFailure("Error de conexión al subir la imagen.");
        reject(new Error("Error de conexión"));
      };

      xhr.send(formData);
    });
  }

  handleUploadFailure(message) {
    alert(`⚠️ Error de carga: ${message}`);
    this.previewZone.classList.add('hidden');
    this.idleZone.classList.remove('hidden');
    this.selectedFile = null;
    this.onUploadError(message);
  }

  clear() {
    this.selectedFile = null;
    this.uploadedUrl = null;
    this.currentImageUrl = null;
    this.imgPreview.src = '';
    this.fileInfo.textContent = '';
    this.fileInput.value = '';
    this.previewZone.classList.add('hidden');
    this.progressZone.classList.add('hidden');
    this.idleZone.classList.remove('hidden');
    this.onImageRemoved();
  }

  getValue() {
    return this.uploadedUrl;
  }
}

// Exportación global para navegadores
window.UniversalImageUploader = UniversalImageUploader;
