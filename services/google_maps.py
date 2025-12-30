"""
Сервис для работы с Google Maps API
"""
import aiohttp
from typing import Optional, Tuple
from config import settings


class GoogleMapsService:
    """Сервис для работы с Google Maps"""
    
    def __init__(self):
        self.api_key = settings.GOOGLE_MAPS_API_KEY
        self.geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        self.reverse_geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    
    async def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Получает координаты по адресу
        
        Args:
            address: Адрес для поиска
        
        Returns:
            Tuple[float, float]: (latitude, longitude) или None
        """
        if not self.api_key:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.geocode_url,
                    params={
                        "address": address,
                        "key": self.api_key
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "OK" and data.get("results"):
                            location = data["results"][0]["geometry"]["location"]
                            return (location["lat"], location["lng"])
        except Exception as e:
            print(f"Ошибка при геокодировании: {e}")
        
        return None
    
    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """
        Получает адрес по координатам (reverse geocoding)
        
        Args:
            latitude: Широта
            longitude: Долгота
        
        Returns:
            str: Адрес или None
        """
        if not self.api_key:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.reverse_geocode_url,
                    params={
                        "latlng": f"{latitude},{longitude}",
                        "key": self.api_key,
                        "language": "ru"  # Русский язык для адресов
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "OK" and data.get("results"):
                            # Возвращаем форматированный адрес
                            return data["results"][0]["formatted_address"]
        except Exception as e:
            print(f"Ошибка при обратном геокодировании: {e}")
        
        return None
    
    def get_map_url(self, latitude: float, longitude: float, zoom: int = 15) -> str:
        """
        Генерирует URL для отображения карты Google Maps
        
        Args:
            latitude: Широта
            longitude: Долгота
            zoom: Уровень масштабирования (1-20)
        
        Returns:
            str: URL карты
        """
        return f"https://www.google.com/maps?q={latitude},{longitude}&z={zoom}"
    
    def get_static_map_url(self, latitude: float, longitude: float, zoom: int = 15, size: str = "400x400") -> str:
        """
        Генерирует URL для статической карты Google Maps
        
        Args:
            latitude: Широта
            longitude: Долгота
            zoom: Уровень масштабирования (1-20)
            size: Размер изображения (например, "400x400")
        
        Returns:
            str: URL статической карты
        """
        if not self.api_key:
            return self.get_map_url(latitude, longitude, zoom)
        
        marker = f"{latitude},{longitude}"
        return (
            f"https://maps.googleapis.com/maps/api/staticmap?"
            f"center={latitude},{longitude}&"
            f"zoom={zoom}&"
            f"size={size}&"
            f"markers=color:red|{marker}&"
            f"key={self.api_key}"
        )


google_maps_service = GoogleMapsService()

