import copy
from random import randint
from time import sleep
from urllib.parse import unquote

from core.colors import end, red, green, yellow
from core.config import fuzzes, xsschecker
from core.requester import requester
from core.utils import replaceValue, counter
from core.log import setup_logger

# ===== ML PREFILTER =====
from xsstrike_ml.ml_prefilter import is_malicious

logger = setup_logger(__name__)


def fuzzer(url, params, headers, GET, delay, timeout, WAF, encoding):
    for fuzz in fuzzes:

        # ===== ML PREFILTER CHECK =====
        if not is_malicious(fuzz):
            logger.info(f"[ML-SKIP] {fuzz}")
            continue

        if delay == 0:
            delay = 0

        t = delay + randint(delay, delay * 2) + counter(fuzz)
        sleep(t)

        try:
            payload = fuzz
            if encoding:
                payload = encoding(unquote(payload))

            data = replaceValue(params, xsschecker, payload, copy.deepcopy)
            response = requester(url, data, headers, GET, delay / 2, timeout)

        except:
            logger.error('WAF is dropping suspicious requests.')
            if delay == 0:
                logger.info('Delay has been increased to %s6%s seconds.' % (green, end))
                delay += 6

            limit = (delay + 1) * 50
            while limit > 0:
                logger.info(
                    '\rFuzzing will continue after %s%i%s seconds.\t\t\r'
                    % (green, limit, end)
                )
                limit -= 1
                sleep(1)

            try:
                requester(url, params, headers, GET, 0, 10)
                logger.good(
                    'Pheww! Looks like sleeping for %s%i%s seconds worked!'
                    % (green, ((delay + 1) * 2), end)
                )
            except:
                logger.error('\nLooks like WAF has blocked our IP Address. Sorry!')
                break

        # ===== RESPONSE ANALYSIS =====
        if payload.lower() in response.text.lower():
            logger.info(f"[ML-PASS] {fuzz}")
            #result = '%s[passed]  %s' % (green, end)
        elif str(response.status_code).startswith('2') is False:
            result = '%s[blocked] %s' % (red, end)
        else:
            result = '%s[filtered]%s' % (yellow, end)

        #logger.info('%s %s' % (result, payload))
