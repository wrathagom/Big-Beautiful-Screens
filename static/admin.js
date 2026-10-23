// Shared helpers for the admin pages (loaded by admin_base.html before page scripts).

async function signOut() {
    if (typeof Clerk !== 'undefined' && Clerk.loaded) {
        await Clerk.signOut();
    }
    window.location.href = '/auth/logout';
}

// Helper to get Clerk session token for API calls (SaaS mode)
// Returns empty headers in self-hosted mode where Clerk isn't loaded
async function getAuthHeaders() {
    if (typeof Clerk === 'undefined') return {};

    // Wait for Clerk to be ready if needed
    if (!Clerk.loaded) await Clerk.load();
    if (!Clerk.session) return {};

    try {
        const token = await Clerk.session.getToken();
        if (token) {
            return { 'Authorization': `Bearer ${token}` };
        }
    } catch (e) {
        console.error('[Auth] Error getting token:', e);
    }
    return {};
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function toggleExpand(card) {
    card.classList.toggle('expanded');
}

function toggleNavDropdown(btn) {
    const menu = btn.nextElementSibling;
    const wasOpen = menu.classList.contains('show');

    document.querySelectorAll('.nav-dropdown-menu.show').forEach(m => {
        m.classList.remove('show');
    });

    if (!wasOpen) {
        menu.classList.add('show');
    }
}

// Close the nav menu when clicking outside it
document.addEventListener('click', (e) => {
    if (!e.target.closest('.nav-dropdown')) {
        document.querySelectorAll('.nav-dropdown-menu.show').forEach(menu => {
            menu.classList.remove('show');
        });
    }
});
