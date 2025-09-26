document.addEventListener('DOMContentLoaded', function() {
    // Login form handling
    const loginForm = document.getElementById('loginForm');
    const adminLoginBtn = document.getElementById('adminLoginBtn');
    
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(loginForm);
            const data = Object.fromEntries(formData.entries());
            
            // Determine login type from URL
            const isAdminLogin = window.location.search.includes('type=admin');
            const loginUrl = isAdminLogin ? '/admin/login' : '/user/login';
            
            fetch(loginUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            })
            .then(response => {
                if (response.redirected) {
                    window.location.href = response.url;
                }
                return response.json();
            })
            .catch(error => console.error('Error:', error));
        });
    }
    
    // Admin login button (if separate button is used)
    if (adminLoginBtn) {
        adminLoginBtn.addEventListener('click', function() {
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            fetch('/admin/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            })
            .then(response => {
                if (response.redirected) {
                    window.location.href = response.url;
                }
            })
            .catch(error => console.error('Error:', error));
        });
    }
   
});

// Add to your existing auth.js
document.addEventListener('DOMContentLoaded', function() {
    // Password confirmation validation
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', function(e) {
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            const mobile = document.getElementById('mobile').value;
            
            // Mobile number validation
            const mobileRegex = /^\+?[0-9]{10,15}$/;
            if (!mobileRegex.test(mobile)) {
                e.preventDefault();
                alert('Please enter a valid mobile number (10-15 digits, + optional)');
                return false;
            }
            
            // Password validation
            if (password !== confirmPassword) {
                e.preventDefault();
                alert('Passwords do not match!');
                return false;
            }
            
            if (password.length < 6) {
                e.preventDefault();
                alert('Password must be at least 6 characters long!');
                return false;
            }
            
            return true;
        });
    }
});

// Add to static/js/auth.js
document.getElementById('forgotPasswordForm')?.addEventListener('submit', function(e) {
    const email = document.getElementById('email').value;
    if (!email.includes('@')) {
        e.preventDefault();
        alert('Please enter a valid email address');
    }
});
db.password_resets.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 })

document.addEventListener('DOMContentLoaded', function() {
    // Initialize dropdowns
    var dropdownElementList = [].slice.call(document.querySelectorAll('.dropdown-toggle'));
    var dropdownList = dropdownElementList.map(function (dropdownToggleEl) {
        return new bootstrap.Dropdown(dropdownToggleEl);
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', function(event) {
        if (!event.target.matches('.dropdown-toggle') && !event.target.closest('.dropdown-menu')) {
            dropdownList.forEach(function(dropdown) {
                dropdown.hide();
            });
        }
    });
});

document.addEventListener('DOMContentLoaded', function() {
    // Password match validation for signup forms
    const signupForms = document.querySelectorAll('form[action*="signup"]');
    
    signupForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const password = form.querySelector('#password').value;
            const confirmPassword = form.querySelector('#confirm_password').value;
            
            if (password !== confirmPassword) {
                e.preventDefault();
                alert('Passwords do not match!');
                form.querySelector('#confirm_password').focus();
            }
        });
    });
});

//Initialize tooltips
var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl)
})
//support
document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const chatContainer = document.querySelector('.chat-container');
    
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const messageInput = this.querySelector('input');
        const message = messageInput.value.trim();
        
        if (message) {
            // Add user message to chat
            const userMessage = `
                <div class="chat-message user mb-2">
                    <div class="d-flex justify-content-end">
                        <div class="flex-grow-1 me-3 text-end">
                            <div class="fw-bold">You</div>
                            <div class="bg-primary text-white p-2 rounded d-inline-block">${message}</div>
                            <small class="text-muted">Just now</small>
                        </div>
                        <div class="flex-shrink-0">
                            <i class="bi bi-person-circle fs-4 text-muted"></i>
                        </div>
                    </div>
                </div>
            `;
            chatContainer.insertAdjacentHTML('beforeend', userMessage);
            messageInput.value = '';
            
            // Scroll to bottom of chat
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
            // Simulate response after 1 second
            setTimeout(() => {
                const responses = [
                    "I understand your question. Let me check that for you.",
                    "Thanks for your message. Our team will get back to you shortly.",
                    "That's a good question! Here's what I can tell you...",
                    "I'll need to check with our support team about that."
                ];
                const randomResponse = responses[Math.floor(Math.random() * responses.length)];
                
                const supportMessage = `
                    <div class="chat-message support mb-2">
                        <div class="d-flex">
                            <div class="flex-shrink-0">
                                <i class="bi bi-person-circle fs-4 text-primary"></i>
                            </div>
                            <div class="flex-grow-1 ms-3">
                                <div class="fw-bold">Support Agent</div>
                                <div class="bg-white p-2 rounded">${randomResponse}</div>
                                <small class="text-muted">Just now</small>
                            </div>
                        </div>
                    </div>
                `;
                chatContainer.insertAdjacentHTML('beforeend', supportMessage);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }, 1000);
        }
    });
});