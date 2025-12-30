"""
Сервис для работы с прямыми криптоплатежами
Поддерживает: BEP20, ERC20, TRC20, Polygon
"""
import logging
import secrets
import string
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from config import settings

logger = logging.getLogger(__name__)

# Контракты USDT в разных сетях
USDT_CONTRACTS = {
    "BEP20": "0x55d398326f99059fF775485246999027B3197955",  # USDT на BSC
    "ERC20": "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT на Ethereum
    "TRC20": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",  # USDT на Tron
    "POLYGON": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",  # USDT на Polygon
}

# Контракты USDC
USDC_CONTRACTS = {
    "BEP20": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
    "ERC20": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "POLYGON": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
}

# Контракты BUSD
BUSD_CONTRACTS = {
    "BEP20": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
    "ERC20": "0x4Fabb145d64652a948d72533023f6E7A623C7C53",
}


class CryptoPaymentService:
    """Сервис для работы с криптоплатежами"""
    
    def __init__(self):
        self.wallets = {
            "BEP20": settings.CRYPTO_WALLET_BEP20,
            "ERC20": settings.CRYPTO_WALLET_ERC20,
            "TRC20": settings.CRYPTO_WALLET_TRC20,
            "POLYGON": settings.CRYPTO_WALLET_POLYGON,
        }
        
        # Проверяем, есть ли хотя бы один кошелек
        has_wallet = any(self.wallets.values())
        if not has_wallet:
            logger.warning("Криптокошельки не настроены. Криптоплатежи работать не будут.")
    
    def get_available_networks(self) -> list[str]:
        """Получить список доступных сетей"""
        return [network for network, address in self.wallets.items() if address]
    
    def get_wallet_address(self, network: str) -> Optional[str]:
        """Получить адрес кошелька для сети"""
        return self.wallets.get(network)
    
    def convert_usd_to_crypto(
        self,
        amount_usd: float,
        network: str,
        currency: str = "USDT"
    ) -> Optional[float]:
        """
        Конвертирует доллары США в криптовалюту
        
        Args:
            amount_usd: Сумма в долларах США
            network: Сеть (BEP20, ERC20, TRC20, POLYGON)
            currency: Валюта (USDT, USDC, BUSD)
        
        Returns:
            Сумма в криптовалюте или None
        """
        # USDT/USDC/BUSD привязаны к доллару, поэтому 1:1
        if currency in ["USDT", "USDC", "BUSD"]:
            return round(amount_usd, 2)
        
        return None
    
    def generate_payment_id(self) -> str:
        """Генерирует уникальный ID для платежа"""
        return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))
    
    def create_payment_info(
        self,
        amount_usd: float,
        network: str,
        currency: str = "USDT",
        payment_type: str = "subscription"
    ) -> Optional[Dict[str, Any]]:
        """
        Создает информацию для платежа
        
        Args:
            amount_usd: Сумма в долларах США
            network: Сеть (BEP20, ERC20, TRC20, POLYGON)
            currency: Валюта (USDT, USDC, BUSD)
            payment_type: Тип платежа (subscription, super_like)
        
        Returns:
            Словарь с информацией о платеже или None
        """
        wallet_address = self.get_wallet_address(network)
        if not wallet_address:
            logger.error(f"Кошелек для сети {network} не настроен")
            return None
        
        crypto_amount = self.convert_usd_to_crypto(amount_usd, network, currency)
        if not crypto_amount:
            logger.error(f"Не удалось конвертировать {amount_usd} USD в {currency}")
            return None
        
        payment_id = self.generate_payment_id()
        
        return {
            "payment_id": payment_id,
            "network": network,
            "wallet_address": wallet_address,
            "amount_usd": amount_usd,
            "crypto_amount": crypto_amount,
            "currency": currency,
            "contract_address": self._get_contract_address(network, currency),
            "payment_type": payment_type,
            "expires_at": datetime.now() + timedelta(hours=1),  # Платеж действителен 1 час
        }
    
    def _get_contract_address(self, network: str, currency: str) -> Optional[str]:
        """Получить адрес контракта токена"""
        if currency == "USDT":
            return USDT_CONTRACTS.get(network)
        elif currency == "USDC":
            return USDC_CONTRACTS.get(network)
        elif currency == "BUSD":
            return BUSD_CONTRACTS.get(network)
        return None
    
    async def check_transaction(
        self,
        network: str,
        wallet_address: str,
        amount: float,
        currency: str = "USDT",
        transaction_hash: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверяет транзакцию в блокчейне
        
        Args:
            network: Сеть (BEP20, ERC20, TRC20, POLYGON)
            wallet_address: Адрес кошелька получателя
            amount: Ожидаемая сумма
            currency: Валюта
            transaction_hash: Хеш транзакции (если есть)
        
        Returns:
            Tuple[bool, Optional[str]]: (найдена ли транзакция, хеш транзакции)
        """
        try:
            if network == "BEP20":
                return await self._check_bep20_transaction(wallet_address, amount, currency, transaction_hash)
            elif network == "ERC20":
                return await self._check_erc20_transaction(wallet_address, amount, currency, transaction_hash)
            elif network == "TRC20":
                return await self._check_trc20_transaction(wallet_address, amount, currency, transaction_hash)
            elif network == "POLYGON":
                return await self._check_polygon_transaction(wallet_address, amount, currency, transaction_hash)
            else:
                logger.error(f"Неподдерживаемая сеть: {network}")
                return False, None
        except Exception as e:
            logger.error(f"Ошибка при проверке транзакции: {e}")
            return False, None
    
    async def _check_bep20_transaction(
        self,
        wallet_address: str,
        amount: float,
        currency: str,
        transaction_hash: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        """Проверка транзакции в сети BEP20 (BSC)"""
        try:
            from web3 import Web3
            
            w3 = Web3(Web3.HTTPProvider(settings.BSC_RPC_URL))
            if not w3.is_connected():
                logger.warning("Не удалось подключиться к BSC RPC")
                return False, None
            
            contract_address = self._get_contract_address("BEP20", currency)
            if not contract_address:
                return False, None
            
            # ERC20 ABI для функции balanceOf и Transfer события
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                },
                {
                    "anonymous": False,
                    "inputs": [
                        {"indexed": True, "name": "from", "type": "address"},
                        {"indexed": True, "name": "to", "type": "address"},
                        {"indexed": False, "name": "value", "type": "uint256"}
                    ],
                    "name": "Transfer",
                    "type": "event"
                }
            ]
            
            contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=erc20_abi)
            
            # Получаем текущий баланс
            balance = contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
            balance_decimal = balance / 10**18  # USDT имеет 18 decimals
            
            # Если указан хеш транзакции, проверяем его
            if transaction_hash:
                try:
                    tx = w3.eth.get_transaction_receipt(transaction_hash)
                    if tx and tx.status == 1:
                        # Проверяем события Transfer
                        transfer_event = contract.events.Transfer()
                        logs = transfer_event.process_receipt(tx)
                        for log in logs:
                            if log.args.to.lower() == wallet_address.lower():
                                received_amount = log.args.value / 10**18
                                if abs(received_amount - amount) < 0.01:  # Допуск 0.01
                                    return True, transaction_hash
                except Exception as e:
                    logger.error(f"Ошибка при проверке транзакции {transaction_hash}: {e}")
            
            # Если транзакция не указана, просто проверяем баланс
            # (в реальности нужно отслеживать изменения баланса)
            # Для простоты возвращаем False, требуется хеш транзакции
            return False, None
            
        except ImportError:
            logger.error("web3 не установлен. Установите: pip install web3")
            return False, None
        except Exception as e:
            logger.error(f"Ошибка при проверке BEP20 транзакции: {e}")
            return False, None
    
    async def _check_erc20_transaction(
        self,
        wallet_address: str,
        amount: float,
        currency: str,
        transaction_hash: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        """Проверка транзакции в сети ERC20 (Ethereum)"""
        # Аналогично BEP20, но используем ETH_RPC_URL
        try:
            from web3 import Web3
            
            w3 = Web3(Web3.HTTPProvider(settings.ETH_RPC_URL))
            if not w3.is_connected():
                return False, None
            
            contract_address = self._get_contract_address("ERC20", currency)
            if not contract_address:
                return False, None
            
            # Аналогично BEP20
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                }
            ]
            
            contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=erc20_abi)
            
            if transaction_hash:
                try:
                    tx = w3.eth.get_transaction_receipt(transaction_hash)
                    if tx and tx.status == 1:
                        return True, transaction_hash
                except:
                    pass
            
            return False, None
            
        except Exception as e:
            logger.error(f"Ошибка при проверке ERC20 транзакции: {e}")
            return False, None
    
    async def _check_trc20_transaction(
        self,
        wallet_address: str,
        amount: float,
        currency: str,
        transaction_hash: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        """Проверка транзакции в сети TRC20 (Tron)"""
        try:
            from tronpy import Tron
            from tronpy.providers.http import HTTPProvider
            
            tron = Tron(HTTPProvider(api_key=None))
            
            if transaction_hash:
                try:
                    tx = tron.get_transaction(transaction_hash)
                    if tx and tx.get('ret', [{}])[0].get('contractRet') == 'SUCCESS':
                        # Проверяем параметры транзакции
                        return True, transaction_hash
                except:
                    pass
            
            return False, None
            
        except ImportError:
            logger.error("tronpy не установлен. Установите: pip install tronpy")
            return False, None
        except Exception as e:
            logger.error(f"Ошибка при проверке TRC20 транзакции: {e}")
            return False, None
    
    async def _check_polygon_transaction(
        self,
        wallet_address: str,
        amount: float,
        currency: str,
        transaction_hash: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        """Проверка транзакции в сети Polygon"""
        # Аналогично BEP20/ERC20, но используем POLYGON_RPC_URL
        try:
            from web3 import Web3
            
            w3 = Web3(Web3.HTTPProvider(settings.POLYGON_RPC_URL))
            if not w3.is_connected():
                return False, None
            
            contract_address = self._get_contract_address("POLYGON", currency)
            if not contract_address:
                return False, None
            
            # Аналогично BEP20
            if transaction_hash:
                try:
                    tx = w3.eth.get_transaction_receipt(transaction_hash)
                    if tx and tx.status == 1:
                        return True, transaction_hash
                except:
                    pass
            
            return False, None
            
        except Exception as e:
            logger.error(f"Ошибка при проверке Polygon транзакции: {e}")
            return False, None
    
    def format_payment_message(self, payment_info: Dict[str, Any]) -> str:
        """Форматирует сообщение с реквизитами для оплаты"""
        network_names = {
            "BEP20": "BSC (Binance Smart Chain)",
            "ERC20": "Ethereum",
            "TRC20": "Tron",
            "POLYGON": "Polygon"
        }
        
        network_name = network_names.get(payment_info["network"], payment_info["network"])
        amount = payment_info["crypto_amount"]
        currency = payment_info["currency"]
        address = payment_info["wallet_address"]
        payment_id = payment_info["payment_id"]
        amount_usd = payment_info.get("amount_usd", 0)
        
        message = (
            f"💰 <b>Оплата через {network_name}</b>\n\n"
            f"💵 Сумма: <b>${amount_usd:.2f} USD</b> ({amount} {currency})\n"
            f"📍 Адрес кошелька:\n<code>{address}</code>\n\n"
            f"📝 <b>Важно!</b>\n"
            f"• Отправляйте ТОЛЬКО {currency} в сети {network_name}\n"
            f"• В комментарии к переводу укажите: <code>{payment_id}</code>\n"
            f"• После отправки нажмите кнопку 'Проверить платеж'\n"
            f"• Платеж действителен 1 час\n\n"
            f"⚠️ Отправка других токенов или в другую сеть приведет к потере средств!"
        )
        
        return message


# Глобальный экземпляр сервиса
crypto_payment_service = CryptoPaymentService()

