document.addEventListener('DOMContentLoaded', async () => {
    // --- Auth Check ---
    if (localStorage.getItem('xai_logged_in') !== 'true') {
        window.location.href = '/';
        return;
    }

    const userNameEl = document.getElementById('userName');
    const userHandleEl = document.getElementById('userHandle');
    const userAvatarEl = document.getElementById('userAvatar');
    const repoGrid = document.getElementById('repoGrid');
    const logoutBtn = document.getElementById('logoutBtn');

    const statusBox = document.getElementById('statusMessage');
    const statusText = document.getElementById('statusText');
    const statusIcon = statusBox.querySelector('.status-icon');

    // --- Logout Handling ---
    logoutBtn.addEventListener('click', async () => {
        localStorage.removeItem('xai_logged_in');
        
        // Call backend to clear HTTPOnly cookie
        await fetch('/api/auth/logout', { method: 'POST' });
        window.location.href = '/';
    });

    try {
        // --- Fetch User Profile ---
        const userRes = await fetch('/api/user');
        if (!userRes.ok) {
            throw new Error("Session expired");
        }
        const user = await userRes.json();
        
        userNameEl.textContent = user.name || user.login;
        userHandleEl.textContent = `@${user.login}`;
        
        // Re-create the avatar element as an img
        const img = document.createElement('img');
        img.src = user.avatar_url;
        img.className = 'user-avatar';
        img.alt = 'User Avatar';
        userAvatarEl.replaceWith(img);

        // --- Fetch Repositories ---
        const reposRes = await fetch('/api/user/repos');
        if (!reposRes.ok) {
            throw new Error("Failed to load repositories");
        }
        const repos = await reposRes.json();
        
        repoGrid.innerHTML = ''; // Clear loader
        
        if (repos.length === 0) {
            repoGrid.innerHTML = '<p style="color: #a0a0b0; grid-column: 1/-1;">No repositories found on this GitHub account.</p>';
            return;
        }

        // Render Cards
        repos.forEach(repo => {
            const card = document.createElement('div');
            card.className = 'repo-card';

            const privacyBadge = repo.private ? 
                '<span class="repo-badge"><i data-feather="lock" style="width: 10px; height: 10px;"></i> Private</span>' : 
                '<span class="repo-badge"><i data-feather="globe" style="width: 10px; height: 10px;"></i> Public</span>';
            
            const connectBtnHtml = repo.is_connected
                ? `<button class="connect-btn" style="background: var(--success-color); color: white; border-color: transparent;" disabled>
                     <i data-feather="check" style="width: 14px; height: 14px;"></i> Connected
                   </button>`
                : `<button class="connect-btn" data-repo="${repo.full_name}">
                     <i data-feather="zap" style="width: 14px; height: 14px;"></i> Connect AI
                   </button>`;

            card.innerHTML = `
                <div class="repo-header">
                    <div>
                        <h3 class="repo-name">${repo.name}</h3>
                        ${privacyBadge}
                    </div>
                </div>
                <p class="repo-desc">${repo.description || 'No description provided.'}</p>
                <div class="repo-footer">
                    <span class="repo-lang">
                        <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:#a855f7; margin-right:4px;"></span>
                        ${repo.language || 'Code'}
                    </span>
                    ${connectBtnHtml}
                </div>
            `;
            repoGrid.appendChild(card);
        });
        feather.replace();

        // --- Attach Connect Events ---
        document.querySelectorAll('.connect-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const repoFullName = e.currentTarget.getAttribute('data-repo');
                await connectRepo(repoFullName, e.currentTarget);
            });
        });

    } catch (err) {
        console.error(err);
        localStorage.removeItem('xai_logged_in');
        window.location.href = '/?error=session_expired';
    }

    // --- Connect Logic ---
    async function connectRepo(repoFullName, btnElement) {
        const originalText = btnElement.innerHTML;
        btnElement.innerHTML = '<i data-feather="loader" class="spin"></i> Connecting...';
        btnElement.disabled = true;
        feather.replace();

        try {
            const res = await fetch('/api/register-repo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ repo_full_name: repoFullName })
            });
            const data = await res.json();

            if (res.ok) {
                showStatus('success', `Successfully connected XAI Reviewer to ${repoFullName}!`);
                btnElement.innerHTML = '<i data-feather="check"></i> Connected';
                btnElement.style.background = 'var(--success-color)';
                btnElement.style.color = 'white';
                btnElement.style.borderColor = 'transparent';
                btnElement.disabled = true;
            } else {
                showStatus('error', data.detail || `Failed to connect ${repoFullName}`);
                btnElement.innerHTML = originalText;
                btnElement.disabled = false;
            }
        } catch (error) {
            console.error(error);
            showStatus('error', 'Network error while configuring webhook.');
            btnElement.innerHTML = originalText;
            btnElement.disabled = false;
        }
        feather.replace();
        
        // Hide status after 5 seconds to keep dashboard clean
        setTimeout(hideStatus, 5000);
    }
    
    // --- Helpers ---
    function showStatus(type, message) {
        statusBox.className = `status-message ${type}`;
        statusText.textContent = message;
        
        if (type === 'success') {
            statusIcon.setAttribute('data-feather', 'check-circle');
            statusBox.style.background = 'rgba(16, 185, 129, 0.1)';
            statusBox.style.borderColor = 'rgba(16, 185, 129, 0.2)';
            statusBox.style.color = '#34d399';
        } else {
            statusIcon.setAttribute('data-feather', 'alert-circle');
            statusBox.style.background = 'rgba(239, 68, 68, 0.1)';
            statusBox.style.borderColor = 'rgba(239, 68, 68, 0.2)';
            statusBox.style.color = '#f87171';
        }
        feather.replace();
    }

    function hideStatus() {
        statusBox.classList.add('hidden');
    }
});
