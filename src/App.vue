<script>
export default {
  data() {
    return {
      showSubmissionWindow: false,
      selectedFile: null,
      metadata: {
        userId: '',
        subjectId: '',
        activity: '',
        shoeType: '',
        acqDatetime: ''
      },
      isUploading: false,
      uploadProgress: 0,
      uploadError: null,
      uploadSuccess: false,
      backendUrl: 'http://localhost:8000'
    }
  },
  computed: {
    isFormValid() {
      return this.metadata.userId.trim() !== '' &&
             this.metadata.subjectId.trim() !== '' &&
             this.metadata.activity.trim() !== '' &&
             this.metadata.shoeType.trim() !== '' &&
             this.metadata.acqDatetime !== ''
    },
    canSubmit() {
      return this.isFormValid && !this.isUploading && this.selectedFile
    }
  },
  methods: {
    triggerFileInput() {
      document.getElementById('video-upload').click()
    },
    handleFileSelection(event) {
      const file = event.target.files[0]
      if (file) {
        this.selectedFile = file
        this.showSubmissionWindow = true
      }
    },
    closeSubmissionWindow() {
      this.showSubmissionWindow = false
      this.selectedFile = null
      this.isUploading = false
      this.uploadProgress = 0
      this.uploadError = null
      this.uploadSuccess = false
      // Reset metadata
      this.metadata = {
        userId: '',
        subjectId: '',
        activity: '',
        shoeType: '',
        acqDatetime: ''
      }
      // Reset file input
      document.getElementById('video-upload').value = ''
    },
    async finalizeSubmission() {
      if (!this.canSubmit) {
        return
      }
      
      this.isUploading = true
      this.uploadError = null
      this.uploadSuccess = false
      this.uploadProgress = 0
      
      try {
        // Create FormData for multipart upload
        const formData = new FormData()
        formData.append('file', this.selectedFile)
        formData.append('user_id', this.metadata.userId)
        formData.append('subject_id', this.metadata.subjectId)
        formData.append('activity', this.metadata.activity)
        formData.append('shoe_type', this.metadata.shoeType)
        formData.append('acq_datetime', this.metadata.acqDatetime)
        
        // Create XMLHttpRequest for upload progress tracking
        const xhr = new XMLHttpRequest()
        
        // Track upload progress
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            this.uploadProgress = Math.round((event.loaded / event.total) * 100)
          }
        })
        
        // Handle response
        const uploadPromise = new Promise((resolve, reject) => {
          xhr.onload = () => {
            if (xhr.status === 200) {
              try {
                const response = JSON.parse(xhr.responseText)
                resolve(response)
              } catch (e) {
                reject(new Error('Invalid response format'))
              }
            } else {
              try {
                const error = JSON.parse(xhr.responseText)
                reject(new Error(error.detail || 'Upload failed'))
              } catch (e) {
                reject(new Error(`Upload failed with status ${xhr.status}`))
              }
            }
          }
          
          xhr.onerror = () => reject(new Error('Network error during upload'))
          xhr.ontimeout = () => reject(new Error('Upload timed out'))
        })
        
        // Start the upload
        xhr.open('POST', `${this.backendUrl}/upload`)
        xhr.timeout = 300000 // 5 minute timeout
        xhr.send(formData)
        
        // Wait for completion
        const result = await uploadPromise
        
        console.log('Upload successful:', result)
        this.uploadSuccess = true
        this.uploadProgress = 100
        
        // Show success message and close after delay
        setTimeout(() => {
          this.closeSubmissionWindow()
        }, 2000)
        
      } catch (error) {
        console.error('Upload failed:', error)
        this.uploadError = error.message || 'Upload failed. Please try again.'
        this.isUploading = false
        this.uploadProgress = 0
      }
    }
  }
}
</script>

<template>
  <div class="app-layout">
    <!-- Navbar Section -->
    <nav class="navbar">
      <div class="nav-left">
        <a href="#home" class="home-button">DANCER</a>
      </div>
      <div class="nav-items">
        <a href="#signup">sign up</a>
        <a href="#learn">learn more</a>
        <a href="#team">study team</a>
        <a href="#funding">funding</a>
      </div>
    </nav>

    <!-- Main Body Section -->
    <main class="main-body">
      <header class="centered-header">
        <h1>DANCER</h1>
        <p class="subtitle">Patient-partnered tracking of neuromuscular disease state and progression from single videos</p>
        <button class="submit-button" @click="triggerFileInput">Submit file</button>
        <input type="file" id="video-upload" accept="video/*" style="display: none;" @change="handleFileSelection">
        <img src="@/assets/prelim_diagram.jpg" alt="DANCER Preliminary Diagram" class="diagram-image" />
      </header>
    </main>

    <!-- Submission Window Modal -->
    <div v-if="showSubmissionWindow" class="modal-overlay">
      <div class="submission-window">
        <div class="submission-header">
          <h2>File Submission</h2>
          <button class="close-button" @click="closeSubmissionWindow">×</button>
        </div>
        <div class="submission-content">
          <p v-if="selectedFile" class="selected-file">Selected file: {{ selectedFile.name }}</p>
          
          <form class="metadata-form">
            <div class="form-group">
              <label for="userId">User ID</label>
              <input 
                type="text" 
                id="userId" 
                v-model="metadata.userId" 
                placeholder="Enter your user ID"
                class="form-input"
              />
            </div>

            <div class="form-group">
              <label for="subjectId">Subject ID</label>
              <input 
                type="text" 
                id="subjectId" 
                v-model="metadata.subjectId" 
                placeholder="Enter the subject ID"
                class="form-input"
              />
            </div>

            <div class="form-group">
              <label for="activity">Activity</label>
              <input 
                type="text" 
                id="activity" 
                v-model="metadata.activity" 
                placeholder="Enter the activity code"
                class="form-input"
              />
            </div>

            <div class="form-group">
              <label for="shoeType">Shoe type</label>
              <input 
                type="text" 
                id="shoeType" 
                v-model="metadata.shoeType" 
                placeholder="Enter the shoe type"
                class="form-input"
              />
            </div>

            <div class="form-group">
              <label for="acqDatetime">Acq_datetime</label>
              <input 
                type="datetime-local" 
                id="acqDatetime" 
                v-model="metadata.acqDatetime" 
                class="form-input"
              />
            </div>
          </form>
          
          <!-- Upload Status Messages -->
          <div v-if="uploadError" class="upload-status error">
            <p>❌ {{ uploadError }}</p>
          </div>
          
          <div v-if="uploadSuccess" class="upload-status success">
            <p>✅ Upload completed successfully!</p>
          </div>
          
          <!-- Upload Progress -->
          <div v-if="isUploading" class="upload-progress">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
            </div>
            <p class="progress-text">Uploading... {{ uploadProgress }}%</p>
          </div>
          
          <div class="submission-actions">
            <button 
              class="finalize-button"
              :class="{ 'disabled': !canSubmit }"
              :disabled="!canSubmit"
              @click="finalizeSubmission"
            >
              {{ isUploading ? 'Uploading...' : 'Finalize submission' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
