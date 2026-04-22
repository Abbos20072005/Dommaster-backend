# atmos_auth.py
import base64, os, time, logging
import requests
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

_token: dict = {}
_creds = base64.b64encode(
    f"{os.environ['ATMOS_KEY']}:{os.environ['ATMOS_SECRET']}".encode()
).decode()

class AtmosAuthService:
    @staticmethod
    def get_access_token() -> str:
        if _token.get("value") and time.time() < _token["expires_at"] - 60:
            return _token["value"]

        res = requests.post(
            url="https://apigw.atmos.uz/token",
            headers={
                "Authorization": f"Basic {_creds}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data="grant_type=client_credentials",
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()

        _token["value"] = data["access_token"]
        _token["expires_at"] = time.time() + data.get("expires_in", 3600)
        logger.info("Atmos token refreshed, expires in %ss", data.get("expires_in", 3600))
        return _token["value"]
    
    @staticmethod
    def refresh_access_token(access_token: str) -> str:
        res = requests.post(
            url="https://apigw.atmos.uz/token",
            headers={
                "Authorization": f"Basic {_creds}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data=f"grant_type=client_credentials&refresh_token={access_token}",
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()

        _token["value"] = data["access_token"]
        _token["expires_at"] = time.time() + data.get("expires_in", 3600)
        logger.info("Atmos token refreshed via refresh_token, expires in %ss", data.get("expires_in", 3600))
        return _token["value"]
    
    @staticmethod
    def cancel_access_token(access_token: str) -> dict:
        res = requests.post(
            url="https://apigw.atmos.uz/revoke",
            headers={
                "Authorization": f"Basic {_creds}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data=f"token={access_token}",
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        logger.info("Atmos token revoked")
        return data

class AtmosBindWithCheckoutService:
    @staticmethod
    def create_card_bind_session(
        access_token: str,
        request_id: str,
        store_id: str,
        account: str,
        success_url: str,
    ) -> dict:
        response = requests.post(
            url="https://apigw.atmos.uz/checkout/card-bind/create",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "request_id": request_id,
                "store_id": store_id,
                "account": account,
                "success_url": success_url,
            },
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    
    @staticmethod
    def get_card_details(access_token: str, card_id: int) -> dict:
        response = requests.get(
            url=f"https://apigw.atmos.uz/mps/pay/card/{card_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=5,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_cards_list(access_token: str):
        response = requests.post(
            url=f"https://apigw.atmos.uz/partner/list-cards",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "page": 1,
                "page_size": 10
            },
            timeout=5,
        )
        response.raise_for_status()
        return response.json()



class AtmosTransactionService:
    @staticmethod
    def create_transaction(amount: int, account: str, store_id: int, access_token: str, lang="ru"):
        res = requests.post(
            url="https://apigw.atmos.uz/merchant/pay/create",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "amount": amount,
                "account": account,
                "terminal_id": os.environ["ATMOS_TERMINAL_ID"],
                "store_id": store_id,
                "lang": lang
            },
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data
    
    @staticmethod
    def pre_apply_transaction(access_token: str, store_id: int, transaction_id: int, card_token: str = None, card_number: str = None, expiry: str = None):
        if card_token:
            json_data = {
                "card_token": card_token,
                "store_id": store_id,
                "transaction_id": transaction_id
            }
        else:
            json_data = {
                "card_number": card_number,
                "expiry": expiry,
                "store_id": store_id,
                "transaction_id": transaction_id
            } 
            
        res = requests.post(
            url="https://apigw.atmos.uz/merchant/pay/create",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=json_data,
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data
    
    @staticmethod
    def apply_transaction(access_token: str, transaction_id: int, otp: str, store_id: int):
        res = requests.post(
            url="https://apigw.atmos.uz/merchant/pay/apply",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "transaction_id": transaction_id,
                "otp": otp,
                "store_id": store_id
            },
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def create_bulk_transaction(access_token: str, store_id: int, params: list):
        res = requests.post(
            url="https://apigw.atmos.uz/merchant/bulk/pay/create",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "store_id": store_id,
                "params": params
            },
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def pre_apply_bulk_transaction(access_token: str, store_id: int, transaction_id: list, card_token=None, card_number=None, expiry=None):
        json_data = {
            "store_id": store_id,
            "transaction_id": transaction_id
        }
        if card_token:
            json_data["card_token"] = card_token
        else:
            json_data["card_number"] = card_number
            json_data["expiry"] = expiry
            
        res = requests.post(
            url="https://apigw.atmos.uz/merchant/bulk/pay/pre-apply",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=json_data,
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def apply_bulk_transaction(access_token: str, store_id: int, transaction_id: list, otp: str):
        res = requests.post(
            url="https://apigw.atmos.uz/merchant/bulk/pay/apply",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "store_id": store_id,
                "otp": otp,
                "transaction_id": transaction_id
            },
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def retry_otp(access_token: str, store_id: int, transaction_id: int):
        res = requests.post(
            url="https://apigw.atmos.uz/merchant/pay/retry-otp",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "store_id": store_id,
                "transaction_id": transaction_id
            },
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def reverse_transaction(access_token: str, transaction_id: int, reason: str = None, hold_amount: int = None):
        json_data = {"transaction_id": transaction_id}
        if reason:
            json_data["reason"] = reason
        if hold_amount:
            json_data["hold_amount"] = hold_amount
            
        res = requests.post(
            url="https://apigw.atmos.uz/merchant/pay/reverse",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=json_data,
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def get_transaction(access_token: str, store_id: int, transaction_id: int):
        res = requests.post(
            url="https://apigw.atmos.uz/merchant/pay/get",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "store_id": store_id,
                "transaction_id": transaction_id
            },
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def create_partial_reverse(access_token: str, transaction_id: int, store_id: int, amount: int, reason: str = None, request_id: str = None, lang: str = None):
        json_data = {
            "transaction_id": transaction_id,
            "store_id": store_id,
            "amount": amount
        }
        if reason:
            json_data["reason"] = reason
        if request_id:
            json_data["request_id"] = request_id
        if lang:
            json_data["lang"] = lang
            
        res = requests.post(
            url="https://apigw.atmos.uz/merchant/pay/create-reverse-partial",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=json_data,
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def confirm_partial_reverse(access_token: str, transaction_id: int, transaction_partial_reverse_id: int, store_id: int, ofd_items: list, request_id: str = None, lang: str = None):
        json_data = {
            "transaction_id": transaction_id,
            "transaction_partial_reverse_id": transaction_partial_reverse_id,
            "store_id": store_id,
            "ofd_items": ofd_items
        }
        if request_id:
            json_data["request_id"] = request_id
        if lang:
            json_data["lang"] = lang
            
        res = requests.post(
            url="https://apigw.atmos.uz/merchant/pay/confirm-reverse-partial",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=json_data,
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def get_partial_reverse(access_token: str, transaction_id: int, transaction_partial_reverse_id: int, store_id: int, lang: str = None):
        json_data = {
            "transaction_id": transaction_id,
            "transaction_partial_reverse_id": transaction_partial_reverse_id,
            "store_id": store_id
        }
        if lang:
            json_data["lang"] = lang
            
        res = requests.post(
            url="https://apigw.atmos.uz/merchant/pay/get-reverse-partial",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=json_data,
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data


class AtmosCardService:
    @staticmethod
    def bind_card_init(access_token: str, card_number: str, expiry: str):
        res = requests.post(
            url="https://apigw.atmos.uz/partner/bind-card/init",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "card_number": card_number,
                "expiry": expiry
            },
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def bind_card_confirm(access_token: str, transaction_id: int, otp: str):
        res = requests.post(
            url="https://apigw.atmos.uz/partner/bind-card/confirm",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "transaction_id": transaction_id,
                "otp": otp
            },
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def list_cards(access_token: str, page: int = None, page_size: int = None):
        json_data = {}
        if page:
            json_data["page"] = page
        if page_size:
            json_data["page_size"] = page_size
            
        res = requests.post(
            url="https://apigw.atmos.uz/partner/list-cards",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=json_data,
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def remove_card(access_token: str, card_id: int, token: str):
        res = requests.post(
            url="https://apigw.atmos.uz/partner/remove-card",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "id": card_id,
                "token": token
            },
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data


class AtmosHoldService:
    @staticmethod
    def create_hold(access_token: str, store_id: int, account: int, amount: int, duration: int, card_token: str = None, card_number: str = None, card_expiry: str = None, payment_details: str = None):
        json_data = {
            "store_id": store_id,
            "account": account,
            "amount": amount,
            "duration": duration,
            "payment_details": ""
        }
        if card_token:
            json_data["card_token"] = card_token
        if card_number:
            json_data["card_number"] = card_number
        if card_expiry:
            json_data["card_expiry"] = card_expiry
        if payment_details:
            json_data["payment_details"] = payment_details

        print("Creating hold with data: ", json_data)
        print("Access token: ", access_token)
            
        res = requests.post(
            url="https://apigw.atmos.uz/hold/create",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=json_data,
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def apply_hold(access_token: str, hold_id: int, otp: str):
        res = requests.put(
            url=f"https://apigw.atmos.uz/hold/apply/{hold_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "otp": otp
            },
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def create_multiple_hold(access_token: str, card_token: str, duration: str, items: list):
        res = requests.post(
            url="https://apigw.atmos.uz/hold/multiple/create",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "card_token": card_token,
                "duration": duration,
                "items": items
            },
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def apply_multiple_hold(access_token: str, parent_id: int, otp: str):
        res = requests.put(
            url=f"https://apigw.atmos.uz/hold/multiple/apply/{parent_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "otp": otp
            },
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def charge_hold(access_token: str, hold_id: int, amount: int = None):
        json_data = {}
        if amount:
            json_data["amount"] = amount
            
        res = requests.post(
            url=f"https://apigw.atmos.uz/hold/{hold_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=json_data,
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def cancel_hold(access_token: str, hold_id: int, send_cancel_sms: bool = True):
        res = requests.delete(
            url=f"https://apigw.atmos.uz/hold/{hold_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "send_cancel_sms": send_cancel_sms
            },
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data

    @staticmethod
    def get_hold(access_token: str, hold_id: int):
        res = requests.get(
            url=f"https://apigw.atmos.uz/hold/{hold_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            timeout=5,
        )
        res.raise_for_status()
        data = res.json()
        return data
    
# print(AtmosAuthService.get_access_token())
# print(AtmosTransactionService.create_transaction(amount=50000, account=123, store_id=10511, access_token="eyJ4NXQiOiJNell4TW1Ga09HWXdNV0kwWldObU5EY3hOR1l3WW1NNFpUQTNNV0kyTkRBelpHUXpOR00wWkdSbE5qSmtPREZrWkRSaU9URmtNV0ZoTXpVMlpHVmxOZyIsImtpZCI6Ik16WXhNbUZrT0dZd01XSTBaV05tTkRjeE5HWXdZbU00WlRBM01XSTJOREF6WkdRek5HTTBaR1JsTmpKa09ERmtaRFJpT1RGa01XRmhNelUyWkdWbE5nX1JTMjU2IiwiYWxnIjoiUlMyNTYifQ.eyJzdWIiOiJhZG1pbiIsImF1dCI6IkFQUExJQ0FUSU9OIiwiYXVkIjoiMVB1YjQycFBEVkdZVl9wcktVaFpSSlRxWUlrYSIsIm5iZiI6MTc3MTU2MzA0NSwiYXpwIjoiMVB1YjQycFBEVkdZVl9wcktVaFpSSlRxWUlrYSIsInNjb3BlIjoiZGVmYXVsdCIsImlzcyI6Imh0dHBzOlwvXC9hcGltYW4uYXRtb3MudXo6OTQ0M1wvb2F1dGgyXC90b2tlbiIsImV4cCI6MTc3MTU2NjY0NSwiaWF0IjoxNzcxNTYzMDQ1LCJqdGkiOiIzODJlMmViMi1mNTkxLTQ0MWMtOTEzZi0wOWRjNTc1NDEzYTcifQ.tHygK7MzXB6K1cQoJIrYgDUJyBm1fbWCic8Il6lK-B9U0AvdHrWkCbE5qu6cnFfW081Cfhv4Xx_rOYTv0mxeVYbMasfBVy5ohWwcYVUh2nileoDuMBpni80o09vrjPU7Kj8ouw4JMTZdmuCrMHKI0ypRzwt4d61pj82mzfwzUE_sXqEXSQ5NBp6d8wvTxwYj0t9xTFUOb5VrE3BTV-55VaCTJZOnzpltoirvvX7IXxUL5QMRkbMmTnQpNlw4PHEra2Vxhy3McC8-d8-3nctTCnFj7cBeXKyCVGuCwtI6mD2eT-Fa-JWteo-Bnmig_-v3lykKNriFsRqqzkaUFN5P7g"))

# print(AtmosTransactionService.pre_apply_transaction(transaction_id=250268, store_id=10511, card_number=5614688715378807, expiry=2903, access_token="eyJ4NXQiOiJNell4TW1Ga09HWXdNV0kwWldObU5EY3hOR1l3WW1NNFpUQTNNV0kyTkRBelpHUXpOR00wWkdSbE5qSmtPREZrWkRSaU9URmtNV0ZoTXpVMlpHVmxOZyIsImtpZCI6Ik16WXhNbUZrT0dZd01XSTBaV05tTkRjeE5HWXdZbU00WlRBM01XSTJOREF6WkdRek5HTTBaR1JsTmpKa09ERmtaRFJpT1RGa01XRmhNelUyWkdWbE5nX1JTMjU2IiwiYWxnIjoiUlMyNTYifQ.eyJzdWIiOiJhZG1pbiIsImF1dCI6IkFQUExJQ0FUSU9OIiwiYXVkIjoiMVB1YjQycFBEVkdZVl9wcktVaFpSSlRxWUlrYSIsIm5iZiI6MTc3MTU2MzA0NSwiYXpwIjoiMVB1YjQycFBEVkdZVl9wcktVaFpSSlRxWUlrYSIsInNjb3BlIjoiZGVmYXVsdCIsImlzcyI6Imh0dHBzOlwvXC9hcGltYW4uYXRtb3MudXo6OTQ0M1wvb2F1dGgyXC90b2tlbiIsImV4cCI6MTc3MTU2NjY0NSwiaWF0IjoxNzcxNTYzMDQ1LCJqdGkiOiIzODJlMmViMi1mNTkxLTQ0MWMtOTEzZi0wOWRjNTc1NDEzYTcifQ.tHygK7MzXB6K1cQoJIrYgDUJyBm1fbWCic8Il6lK-B9U0AvdHrWkCbE5qu6cnFfW081Cfhv4Xx_rOYTv0mxeVYbMasfBVy5ohWwcYVUh2nileoDuMBpni80o09vrjPU7Kj8ouw4JMTZdmuCrMHKI0ypRzwt4d61pj82mzfwzUE_sXqEXSQ5NBp6d8wvTxwYj0t9xTFUOb5VrE3BTV-55VaCTJZOnzpltoirvvX7IXxUL5QMRkbMmTnQpNlw4PHEra2Vxhy3McC8-d8-3nctTCnFj7cBeXKyCVGuCwtI6mD2eT-Fa-JWteo-Bnmig_-v3lykKNriFsRqqzkaUFN5P7g"))
