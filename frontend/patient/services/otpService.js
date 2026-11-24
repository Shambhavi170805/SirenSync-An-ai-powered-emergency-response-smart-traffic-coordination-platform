/**
 * SirenSync - Phone OTP Verification API Service
 *
 * Required Backend API Contract:
 * - POST /api/v1/auth/otp/send   Body: { phoneNumber: string }
 *   Response: { success: boolean, cooldownSeconds?: number, expiresAt?: string, message?: string }
 *
 * - POST /api/v1/auth/otp/verify Body: { phoneNumber: string, otp: string }
 *   Response: { success: boolean, verificationToken: string, verifiedAt: string, message?: string }
 */

const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || '';

export class OtpApiError extends Error {
  constructor(message, status = 0, data = {}) {
    super(message);
    this.name = 'OtpApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Request an SMS OTP from the server
 * @param {string} phoneNumber
 * @returns {Promise<{ success: boolean, cooldownSeconds: number }>}
 */
export async function sendPhoneOtp(phoneNumber) {
  if (!phoneNumber || phoneNumber.trim() === '') {
    throw new OtpApiError('A valid phone number is required to send verification code.', 400);
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/otp/send`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ phoneNumber: phoneNumber.trim() })
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      if (response.status === 429) {
        throw new OtpApiError(
          data.message || 'Too many OTP requests. Please wait for the cooldown to expire or call 112.',
          429,
          data
        );
      }
      if (response.status === 404 || response.status === 503) {
        throw new OtpApiError(
          data.message || 'SMS OTP verification service is not running or unconfigured on backend. Production SMS provider required.',
          response.status,
          data
        );
      }
      throw new OtpApiError(
        data.message || `Failed to send OTP (Server responded with HTTP ${response.status}).`,
        response.status,
        data
      );
    }

    return {
      success: Boolean(data.success),
      cooldownSeconds: data.cooldownSeconds || 60,
      expiresAt: data.expiresAt || null,
      message: data.message || 'Verification code sent via SMS.'
    };
  } catch (err) {
    if (err instanceof OtpApiError) {
      throw err;
    }
    // Network failure (server not reachable / offline)
    throw new OtpApiError(
      'Unable to connect to SMS verification service. Backend API is currently unconfigured or offline.',
      0,
      { originalError: err.message }
    );
  }
}

/**
 * Verify submitted OTP against the backend
 * @param {string} phoneNumber
 * @param {string} otp
 * @returns {Promise<{ success: boolean, verificationToken: string }>}
 */
export async function verifyPhoneOtp(phoneNumber, otp) {
  if (!phoneNumber || !otp || otp.length !== 6) {
    throw new OtpApiError('A complete 6-digit verification code is required.', 400);
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/otp/verify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        phoneNumber: phoneNumber.trim(),
        otp: otp.trim()
      })
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      if (response.status === 400) {
        throw new OtpApiError(
          data.message || 'Incorrect verification code. Please check your SMS and try again.',
          400,
          data
        );
      }
      if (response.status === 410) {
        throw new OtpApiError(
          data.message || 'Verification code has expired. Please request a new OTP.',
          410,
          data
        );
      }
      if (response.status === 429) {
        throw new OtpApiError(
          data.message || 'Maximum verification attempts exceeded. Please request a new code.',
          429,
          data
        );
      }
      throw new OtpApiError(
        data.message || `Verification failed (HTTP ${response.status}).`,
        response.status,
        data
      );
    }

    if (!data.verificationToken) {
      throw new OtpApiError('Server responded without verification token.', 500);
    }

    return {
      success: true,
      verificationToken: data.verificationToken,
      verifiedAt: data.verifiedAt || new Date().toISOString(),
      message: data.message || 'Phone number verified successfully.'
    };
  } catch (err) {
    if (err instanceof OtpApiError) {
      throw err;
    }
    throw new OtpApiError(
      'Unable to connect to verification server. Backend API is currently unconfigured or offline.',
      0,
      { originalError: err.message }
    );
  }
}
