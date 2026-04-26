class MLStats:
    total_payloads = 0
    ml_filtered = 0
    sent_to_target = 0
    confirmed_xss = 0

    @classmethod
    def report(cls):
        print("\n====== ML INTEGRATION REPORT ======")
        print(f"Total payloads generated: {cls.total_payloads}")
        print(f"Payloads filtered by ML: {cls.ml_filtered}")
        print(f"Payloads sent to target: {cls.sent_to_target}")
        print(f"Confirmed XSS payloads: {cls.confirmed_xss}")
        print("=================================\n")
