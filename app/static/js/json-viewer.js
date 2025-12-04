// JSON Viewer functionality
window.showJsonViewer = function(data) {
    const modal = document.getElementById('jsonModal');
    const jsonContent = document.getElementById('jsonContent');
    const closeBtn = document.querySelector('.modal-close');
    
    if (modal && jsonContent) {
        // Format JSON with syntax highlighting
        jsonContent.textContent = JSON.stringify(data, null, 2);
        modal.style.display = 'block';
        
        // Close modal when clicking X
        if (closeBtn) {
            closeBtn.onclick = function() {
                modal.style.display = 'none';
            };
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        };
    }
};
