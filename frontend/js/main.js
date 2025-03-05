document.addEventListener('DOMContentLoaded', function() {
    // Sidebar toggle
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebarCollapse) {
        sidebarCollapse.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
    }

    // Notification panel toggle
    const notificationBtn = document.getElementById('notificationBtn');
    const notificationPanel = new bootstrap.Offcanvas(document.getElementById('notificationPanel'));
    
    if (notificationBtn) {
        notificationBtn.addEventListener('click', function() {
            notificationPanel.show();
        });
    }

    // Set active menu item based on current page
    const currentPath = window.location.pathname;
    const menuItems = document.querySelectorAll('#sidebar a');
    
    menuItems.forEach(item => {
        if (item.getAttribute('href') === currentPath) {
            item.parentElement.classList.add('active');
        }
    });

    // Handle analysis submenu
    const analysisSubmenu = document.getElementById('analysisSubmenu');
    if (analysisSubmenu) {
        const analysisLinks = analysisSubmenu.querySelectorAll('a');
        analysisLinks.forEach(link => {
            if (link.getAttribute('href') === currentPath) {
                analysisSubmenu.classList.add('show');
                link.parentElement.classList.add('active');
            }
        });
    }
}); 