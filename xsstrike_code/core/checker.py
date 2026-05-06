import copy
import re
from urllib.parse import unquote

from fuzzywuzzy import fuzz

from core.config import xsschecker
from core.requester import requester
from core.utils import replaceValue, fillHoles
from core.ml_stats import MLStats

# Import ML Postfilter
from xsstrike_ml.postfilter import evaluate_payload


def checker(url, params, headers, GET, delay, payload, positions, timeout, encoding, context=None, is_payload=False):
    """
    Scanner / verification stage
    Now includes ML postfilter validation.
    """

    checkString = 'st4r7s' + payload + '3nd'

    if encoding:
        checkString = encoding(unquote(checkString))

    # ===============================
    # SEND REQUEST
    # ===============================
    response = requester(
        url,
        replaceValue(params, xsschecker, checkString, copy.deepcopy),
        headers,
        GET,
        delay,
        timeout
    )

    #  Handle failed request safely
    if response is None or not hasattr(response, "text"):
        return []

    response_text = response.text.lower()

    # ===============================
    # REFLECTION DETECTION
    # ===============================
    reflectedPositions = [
        match.start() for match in re.finditer('st4r7s', response_text)
    ]

    filledPositions = fillHoles(positions, reflectedPositions)

    efficiencies = []

    # ===============================
    # PROCESS ALL POSITIONS (FIXED)
    # ===============================
    if filledPositions:
        for position in filledPositions:
            try:
                start = position
                end = response_text.find("3nd", start)

                if end != -1:
                    reflected = response_text[start:end + 3]
                else:
                    reflected = response_text[start:start + len(checkString)]

                efficiency = fuzz.partial_ratio(reflected, checkString.lower())

                # Special XSStrike handling
                if reflected[:-2] == (
                    '\\%s' % checkString.replace('st4r7s', '').replace('3nd', '')
                ):
                    efficiency = 90

                # Penalize truncated reflection
                if len(reflected) < len(checkString) * 0.8:
                    efficiency -= 15

                efficiency = max(0, efficiency)

                efficiencies.append(efficiency)

            except Exception:
                continue
    else:
        efficiencies.append(0)

    final_efficiencies = list(filter(None, efficiencies))
    xs_eff = max(final_efficiencies) if final_efficiencies else 0

    # ===============================
    # ML POSTFILTER STAGE
    # ===============================
    if context and is_payload:
        try:
            ml_pred, confidence = evaluate_payload(payload, context)

            # -------------------------------
            # STEP 1: Reflection check
            # -------------------------------
            if xs_eff < 70:
                print("------------------------------------------------------------")
                print("[NO REFLECTION]")
                print("Payload:", payload)
                print(f"XSStrike Efficiency: {xs_eff}")
                print(f"ML Confidence: {confidence:.2f}")
                return []

            # -------------------------------
            # STEP 2: ML decision
            # -------------------------------
            if confidence >= 0.9:
                MLStats.confirmed_xss += 1

                print("------------------------------------------------------------")
                print("[CONFIRMED XSS]")
                print("Payload:", payload)
                print(f"XSStrike Efficiency: {xs_eff}")
                print(f"Postfilter ML Confidence: {confidence:.2f}")

            else:
                print("------------------------------------------------------------")
                print("[REFLECTED BUT REJECTED]")
                print("Payload:", payload)
                print(f"XSStrike Efficiency: {xs_eff}")
                print(f"Postfilter ML Confidence: {confidence:.2f}")
                return []

        except Exception as e:
            print("[ML ERROR]", e)

    return final_efficiencies