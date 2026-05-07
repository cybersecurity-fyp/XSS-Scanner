import copy
import re
from urllib.parse import urlparse, quote, unquote

from core.checker import checker
from core.colors import end, green, que
import core.config
from core.config import xsschecker, minEfficiency
from core.dom import dom
from core.filterChecker import filterChecker
from core.generator import generator
from core.htmlParser import htmlParser
from core.requester import requester
from core.utils import getUrl, getParams, getVar
from core.wafDetector import wafDetector
from core.log import setup_logger

# ML prefilter
from xsstrike_ml.ml_prefilter import is_malicious

# ML stats
from core.ml_stats import MLStats

logger = setup_logger(__name__)


def scan(target, paramData, encoding, headers, delay, timeout, skipDOM, skip):
    GET, POST = (False, True) if paramData else (True, False)

    if not target.startswith('http'):
        try:
            requester('https://' + target, {}, headers, GET, delay, timeout)
            target = 'https://' + target
        except:
            target = 'http://' + target

    logger.debug(f'Scan target: {target}')
    response = requester(target, {}, headers, GET, delay, timeout).text

    if not skipDOM:
        logger.run('Checking for DOM vulnerabilities')
        highlighted = dom(response)
        if highlighted:
            logger.good('Potentially vulnerable objects found')
            logger.red_line(level='good')
            for line in highlighted:
                logger.no_format(line, level='good')
            logger.red_line(level='good')

    url = getUrl(target, GET)
    params = getParams(target, paramData, GET)

    if not params:
        logger.error('No parameters to test.')
        return

    WAF = wafDetector(url, {list(params.keys())[0]: xsschecker}, headers, GET, delay, timeout)

    if WAF:
        logger.error(f'WAF detected: {green}{WAF}{end}')
    else:
        logger.good(f'WAF Status: {green}Offline{end}')

    for paramName in params.keys():
        paramsCopy = copy.deepcopy(params)
        logger.info(f'Testing parameter: {paramName}')

        paramsCopy[paramName] = encoding(xsschecker) if encoding else xsschecker

        response = requester(url, paramsCopy, headers, GET, delay, timeout)
        occurences = htmlParser(response, encoding)
        positions = occurences.keys()

        if not occurences:
            logger.error('No reflection found')
            continue

        logger.info(f'Reflections found: {len(occurences)}')

        logger.run('Analysing reflections')
        filterChecker(url, paramsCopy, headers, GET, delay, occurences, timeout, encoding)

        logger.run('Generating payloads')
        vectors = generator(occurences, response.text)

        total = sum(len(v) for v in vectors.values())

        if total == 0:
            logger.error('No vectors were crafted.')
            continue

        logger.info(f'Payloads generated: {total}')

        MLStats.total_payloads += total

        progress = 0

        with open("xsstrike_payloads_for_postfilter.txt", "a", encoding="utf-8") as f:
            for confidence, vects in vectors.items():
                for vect in vects:

                    f.write(vect + "\n")

                    if core.config.globalVariables['path']:
                        vect = vect.replace('/', '%2F')

                    loggerVector = vect
                    progress += 1
                    logger.run(f'Progress: {progress}/{total}\r')

                    if not GET:
                        vect = unquote(vect)

                    # ===============================
                    # PREFILTER (ML)
                    # ===============================

                    if not is_malicious(vect):
                        MLStats.ml_filtered += 1
                        continue

                    MLStats.sent_to_target += 1

                    # ===============================
                    # SEND TO TARGET
                    # ===============================
                    efficiencies = checker(
                        url,
                        paramsCopy,
                        headers,
                        GET,
                        delay,
                        vect,
                        positions,
                        timeout,
                        encoding,
                        context=occurences[list(occurences.keys())[0]]['context'],
                        is_payload=True
                    )

                    if not efficiencies:
                        efficiencies = [0] * len(occurences)

                    bestEfficiency = max(efficiencies)

                    if not skip:
                        choice = input(f'{que} Would you like to continue scanning? [y/N] ').lower()
                        if choice != 'y':
                            MLStats.report()
                            return

        logger.no_format('')

    MLStats.report()