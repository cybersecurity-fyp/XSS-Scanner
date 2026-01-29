import copy
from urllib.parse import urlparse

from core.colors import green, end
from core.config import xsschecker
from core.fuzzer import fuzzer
from core.requester import requester
from core.utils import getUrl, getParams
from core.wafDetector import wafDetector
from core.log import setup_logger

# ML import – we only use it to confirm ML engine availability
from core.ml_engine import model, vectorizer

logger = setup_logger(__name__)


def singleFuzz(target, paramData, encoding, headers, delay, timeout):
    # ==========================================
    # ML ENGINE STATUS LOG
    # ==========================================
    if model is not None and vectorizer is not None:
        logger.good("[ML] Engine active – payloads will be ML-filtered")
    else:
        logger.warning("[ML] Engine NOT loaded – fuzzing will run normally")

    # ==========================================
    # ORIGINAL XSSTRIKE LOGIC
    # ==========================================
    GET, POST = (False, True) if paramData else (True, False)

    # Fix missing protocol
    if not target.startswith('http'):
        try:
            requester('https://' + target, {}, headers, GET, delay, timeout)
            target = 'https://' + target
        except:
            target = 'http://' + target

    logger.debug(f"Single Fuzz target: {target}")

    host = urlparse(target).netloc
    logger.debug(f"Single fuzz host: {host}")

    url = getUrl(target, GET)
    logger.debug(f"Single fuzz url: {url}")

    params = getParams(target, paramData, GET)
    logger.debug_json("Single fuzz params:", params)

    if not params:
        logger.error("No parameters to test.")
        quit()

    # WAF detection
    WAF = wafDetector(url,
                      {list(params.keys())[0]: xsschecker},
                      headers, GET, delay, timeout)

    if WAF:
        logger.error('WAF detected: %s%s%s' % (green, WAF, end))
    else:
        logger.good('WAF Status: %sOffline%s' % (green, end))

    # ==========================================
    # FUZZING LOOP
    # ==========================================
    for paramName in params.keys():
        logger.info(f"Fuzzing parameter: {paramName}")

        paramsCopy = copy.deepcopy(params)
        paramsCopy[paramName] = xsschecker

        # NOTE: ML filtering happens inside fuzzer() and generator()
        fuzzer(url, paramsCopy, headers, GET, delay, timeout, WAF, encoding)
