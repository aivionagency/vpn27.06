class VpnPanelService:
    def create_key(self, user_telegram_id: int) -> str:
        # TODO: call panel API to create a real key
        return f"vless://demo-{user_telegram_id}-fake-key-for-mvp"

    def get_subscription_status(self, user_telegram_id: int):
        # TODO: Call panel API for actual status
        pass

    def activate(self, user_telegram_id: int, days: int):
        # TODO: Activate key on panel
        pass

    def deactivate(self, user_telegram_id: int):
        # TODO: Deactivate key on panel
        pass
