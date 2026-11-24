/**
 * SirenSync Patient Authentication Service
 * Communicates with FastAPI backend using HTTP-only session cookies
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

async function handleResponse(response) {
  let data = null;
  try {
    data = await response.json();
  } catch (e) {
    // Non-JSON response
  }

  if (!response.ok) {
    const errorDetail = data?.detail || data?.message || `Request failed with status ${response.status}`;
    const error = new Error(typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail));
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

export const authService = {
  /**
   * Registers a new patient account
   */
  async register({ fullName, email, password, confirmPassword, captchaToken }) {
    const response = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // Includes HTTP-only session cookies
      body: JSON.stringify({
        full_name: fullName,
        email: email,
        password: password,
        confirm_password: confirmPassword,
        captcha_token: captchaToken || 'XXXX.DUMMY.TOKEN.XXXX',
      }),
    });

    return handleResponse(response);
  },

  /**
   * Signs in an existing patient
   */
  async login({ email, password, captchaToken }) {
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        email: email,
        password: password,
        captcha_token: captchaToken || 'XXXX.DUMMY.TOKEN.XXXX',
      }),
    });

    return handleResponse(response);
  },

  /**
   * Retrieves the currently authenticated patient's profile from session cookie
   */
  async getCurrentPatient() {
    try {
      const response = await fetch(`${API_BASE}/api/auth/me`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        credentials: 'include',
      });

      if (response.status === 401) {
        return null;
      }

      const data = await handleResponse(response);
      return data?.patient || null;
    } catch (err) {
      if (err.status === 401) {
        return null;
      }
      console.warn('Authentication check failed:', err.message);
      return null;
    }
  },

  /**
   * Signs out patient and clears server session + HTTP-only cookie
   */
  async logout() {
    try {
      const response = await fetch(`${API_BASE}/api/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });
      return handleResponse(response);
    } catch (err) {
      console.warn('Logout error:', err.message);
      return { success: true };
    }
  },
};

export default authService;
