// Form validation
function validateForm(formId, rules) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    form.addEventListener('submit', function(e) {
        let isValid = true;
        for (const [fieldId, rule] of Object.entries(rules)) {
            const field = document.getElementById(fieldId);
            if (!field) continue;
            const value = field.value.trim();
            let error = null;
            
            if (rule.required && !value) {
                error = rule.required;
            } else if (rule.min && parseFloat(value) < rule.min) {
                error = rule.min;
            } else if (rule.pattern && !rule.pattern.test(value)) {
                error = rule.patternMsg;
            }
            
            if (error) {
                e.preventDefault();
                showFieldError(fieldId, error);
                isValid = false;
            } else {
                clearFieldError(fieldId);
            }
        }
        return isValid;
    });
}

function showFieldError(fieldId, message) {
    const field = document.getElementById(fieldId);
    let errorEl = document.getElementById(fieldId + '-error');
    if (!errorEl) {
        errorEl = document.createElement('div');
        errorEl.id = fieldId + '-error';
        errorEl.className = 'text-red-600 text-sm mt-1';
        field.parentNode.insertBefore(errorEl, field.nextSibling);
    }
    errorEl.textContent = typeof message === 'string' ? message : 'Invalid value';
    field.classList.add('border-red-500');
}

function clearFieldError(fieldId) {
    const errorEl = document.getElementById(fieldId + '-error');
    if (errorEl) errorEl.remove();
    const field = document.getElementById(fieldId);
    if (field) field.classList.remove('border-red-500');
}

// Create listing validation
function validateCreateListing() {
    let isValid = true;
    
    const title = document.getElementById('title');
    const price = document.getElementById('price');
    const condition = document.getElementById('condition');
    
    clearFieldError('title');
    clearFieldError('price');
    clearFieldError('condition');
    
    if (!title || !title.value.trim()) {
        showFieldError('title', 'Title is required');
        isValid = false;
    }
    
    if (!price || parseFloat(price.value) <= 0) {
        showFieldError('price', 'Price must be greater than 0');
        isValid = false;
    }
    
    if (!condition || !condition.value) {
        showFieldError('condition', 'Please select a condition');
        isValid = false;
    }
    
    return isValid;
}

// Login validation
function validateLogin() {
    let isValid = true;
    const email = document.getElementById('email');
    const password = document.getElementById('password');
    
    clearFieldError('email');
    clearFieldError('password');
    
    if (!email || !email.value.trim()) {
        showFieldError('email', 'Email is required');
        isValid = false;
    } else if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
        showFieldError('email', 'Please enter a valid email');
        isValid = false;
    }
    
    if (!password || !password.value) {
        showFieldError('password', 'Password is required');
        isValid = false;
    }
    
    return isValid;
}

// Signup validation
function validateSignup() {
    let isValid = true;
    const email = document.getElementById('email');
    const password = document.getElementById('password');
    const confirm = document.getElementById('confirm-password');
    
    clearFieldError('email');
    clearFieldError('password');
    clearFieldError('confirm-password');
    
    if (!email || !email.value.trim()) {
        showFieldError('email', 'Email is required');
        isValid = false;
    } else if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
        showFieldError('email', 'Please enter a valid email');
        isValid = false;
    }
    
    if (!password || password.value.length < 6) {
        showFieldError('password', 'Password must be at least 6 characters');
        isValid = false;
    }
    
    if (confirm && password && password.value !== confirm.value) {
        showFieldError('confirm-password', 'Passwords do not match');
        isValid = false;
    }
    
    return isValid;
}

// Review validation
function validateReview() {
    const rating = document.getElementById('rating-value');
    const errorEl = document.getElementById('rating-error');
    
    if (!rating || !rating.value) {
        if (errorEl) errorEl.classList.remove('hidden');
        return false;
    }
    if (errorEl) errorEl.classList.add('hidden');
    return true;
}

function setRating(value) {
    document.getElementById('rating-value').value = value;
    const stars = document.querySelectorAll('.star-btn');
    stars.forEach((star, index) => {
        star.style.color = index < value ? '#f59e0b' : '#d1d5db';
    });
}
