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
