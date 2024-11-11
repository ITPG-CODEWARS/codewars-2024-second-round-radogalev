let currentUrlId = null;

const Modals = {
    urlOptions: null,
    editUrl: null,

    init() {
        console.log('Initializing Modals...');
        
        // Initialize modal elements
        this.urlOptions = document.getElementById('urlOptionsModal');
        this.editUrl = document.getElementById('editModal');
        
        console.log('URL Options Modal:', this.urlOptions);
        console.log('Edit Modal:', this.editUrl);

        // Add event listeners for close buttons
        const closeButtons = document.querySelectorAll('.close');
        closeButtons.forEach(button => {
            button.addEventListener('click', () => this.closeAll());
        });

        // Close modal when clicking outside
        window.addEventListener('click', (event) => {
            if (event.target === this.urlOptions || event.target === this.editUrl) {
                this.closeAll();
            }
        });

        // Add click handlers for the three dots buttons
        this.setupThreeDotsButtons();

        // Set up QR code download button
        const downloadButton = document.getElementById('downloadQrCode');
        if (downloadButton) {
            downloadButton.addEventListener('click', () => this.downloadQRCode());
        }
    },

    setupThreeDotsButtons() {
        const urlOptionsButtons = document.querySelectorAll('.bx-dots-vertical-rounded');
        console.log('Found three dots buttons:', urlOptionsButtons.length);
        
        urlOptionsButtons.forEach(button => {
            console.log('Setting up button with URL ID:', button.getAttribute('data-url-id'));
            
            // Remove any existing click listeners
            button.replaceWith(button.cloneNode(true));
            
            // Get the fresh button reference
            const newButton = document.querySelector(`[data-url-id="${button.getAttribute('data-url-id')}"]`);
            
            newButton.addEventListener('click', (e) => {
                console.log('Three dots button clicked');
                e.stopPropagation();
                const urlId = newButton.getAttribute('data-url-id');
                console.log('URL ID:', urlId);
                this.openUrlOptionsModal(urlId);
            });
        });
    },

    openUrlOptionsModal(urlId) {
        console.log('Opening URL options modal for URL ID:', urlId);
        if (!urlId) {
            console.error('No URL ID provided');
            return;
        }
        if (!this.urlOptions) {
            console.error('URL options modal element not found');
            return;
        }
        this.open(this.urlOptions, urlId);
    },

    open(modalElement, urlId = null) {
        console.log('Opening modal with URL ID:', urlId);
        if (!modalElement) {
            console.error('Modal element not found');
            return;
        }

        // Close any open modals
        this.closeAll();
        
        // Store current URL ID
        if (urlId) {
            currentUrlId = urlId;
            this.loadUrlDetails(urlId);
        }
        
        modalElement.style.display = 'block';
        console.log('Modal opened');
    },

    close(modalElement) {
        if (modalElement) {
            modalElement.style.display = 'none';
        }
    },

    closeAll() {
        console.log('Closing all modals');
        this.close(this.urlOptions);
        this.close(this.editUrl);
    },

    async loadUrlDetails(urlId) {
        console.log('Loading URL details for ID:', urlId);
        try {
            const response = await fetch(`/api/url/${urlId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Loaded URL details:', data);

            // Update form fields with URL details
            document.getElementById('clickCount').textContent = data.clicks;
            document.getElementById('clickLimit').value = data.click_limit || '';
            document.getElementById('endDate').value = data.end_date || '';
            document.getElementById('customUrl').value = data.short_url || '';

            // Load QR code
            this.loadQRCode(urlId);
        } catch (error) {
            console.error('Error loading URL details:', error);
            alert('Failed to load URL details');
        }
    },

    async loadQRCode(urlId) {
        try {
            const response = await fetch(`/api/url/${urlId}/qr`);
            if (!response.ok) throw new Error('Failed to load QR code');
            
            const data = await response.json();
            const qrContainer = document.getElementById('qrCodeImage');
            qrContainer.innerHTML = `<img src="${data.qr_code}" alt="QR Code">`;
        } catch (error) {
            console.error('Error loading QR code:', error);
            document.getElementById('qrCodeImage').innerHTML = 'Failed to load QR code';
        }
    },

    async downloadQRCode() {
        if (!currentUrlId) {
            alert('No URL selected');
            return;
        }

        try {
            const response = await fetch(`/api/url/${currentUrlId}/qr`);
            const data = await response.json();

            if (!response.ok) throw new Error(data.error || 'Failed to generate QR code');

            const link = document.createElement('a');
            link.href = data.qr_code;
            link.download = 'qr-code.png';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            console.error('Error downloading QR code:', error);
            alert('Failed to download QR code');
        }
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing Modals...');
    Modals.init();

    // Setup event delegation for dynamically added elements
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('bx-dots-vertical-rounded')) {
            console.log('Three dots clicked through delegation');
            const urlId = e.target.getAttribute('data-url-id');
            if (urlId) {
                Modals.openUrlOptionsModal(urlId);
            }
        }
    });
});

// Save URL options function
async function saveUrlOptions() {
    if (!currentUrlId) {
        alert('No URL selected');
        return;
    }

    const updateData = {
        click_limit: document.getElementById('clickLimit').value || null,
        end_date: document.getElementById('endDate').value || null,
        custom_url: document.getElementById('customUrl').value || null
    };

    try {
        const response = await fetch(`/api/url/${currentUrlId}/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updateData)
        });

        const data = await response.json();

        if (response.ok) {
            alert('URL settings updated successfully');
            window.location.reload();
        } else {
            throw new Error(data.error || 'Failed to update URL settings');
        }
    } catch (error) {
        console.error('Error saving URL options:', error);
        alert(error.message);
    }
}

// Delete URL function
async function deleteUrl(urlId) {
    if (!confirm("Are you sure you want to delete this URL?")) {
        return;
    }
    try {
        const response = await fetch(`/api/url/${urlId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (response.ok) {
            alert('URL deleted successfully');
            window.location.reload();
        } else {
            throw new Error(data.error || 'Failed to delete URL');
        }
    } catch (error) {
        console.error('Error deleting URL:', error);
        alert(error.message);
    }
}

// Open edit modal function
function openEditModal() {
    const longUrl = document.getElementById('longUrlInput').value;
    if (!longUrl) {
        alert('Please enter a URL first');
        return;
    }
    document.getElementById('modalLongUrl').value = longUrl;
    Modals.open(Modals.editUrl);
}

// Close edit modal function
function closeEditModal() {
    Modals.close(Modals.editUrl);
}
