from mqtt.mqtt_exceptions import *
import re   # https://docs.pycom.io/firmwareapi/micropython/ure/


class TopicMatcher:
    WILDCARD_ANY = b'#'
    WILDCARD_SIG = b'+'

    def match(self, topic):
        print("Wildcard: " + self.pattern)
        print("Topic: " + topic)
        if topic == self.pattern:
            return []
        elif self.pattern is '#':
            return [topic]
        
        res = []
        t = topic.split('/')
        w = self.pattern.split('/')

        
        for i in range(0, len(t)):
            if w[i] == '+':
                res.append(t[i])
            elif w[i] == '#':
                res.append("/".join(t[1:]))
                return res 
            elif w[i] != t[i]:
                print(w[i] + " is not " + t[i])
                return None;
    
        print(i)
        if w[i] == '#':
            i = i+1

        return res if i == len(w)-1 else None

    def __init__(self, pattern):
        self.pattern = pattern;
        # tokens = self._tokenize(pattern)
        # index = 0
        # for token in tokens:
        #     self._process_token(token, index, tokens)
        #     index = index + 1

    # def _make_regex(self, tokens):
    #     pass

    # def _token_to_regex(self, token, index, tokens):
    #     last = (index == len(tokens) - 1)
    #     before_multi = (index == (len(tokens) - 2)) and (tokens[len(tokens)-1]["type"] == "multi")
    #     return token.last if (last or before_multi) else token.piece

    # def _process_token(self, token, index, tokens):
    #     last = (index == (len(tokens) - 1))
    #     if token[0] == '+':
    #         return self._process_single(token, last)
    #     if token[0] == "#":
    #         return self._process_multi(token,last)
    #     else:
    #         return self._process_raw(token, last)

    # def _process_multi(self, token, last):
    #     if not last:
    #         raise MQTTTopicException("# wildcard must be at the end of the pattern")
        
    #     name = token[1:]
        
    #     return {
    #         "type": "multi",
    #         "name": name,
    #         "piece": "((?:[^/#+]+/)*)",
	# 	    "last": "((?:[^/#+]+/?)*)"
    #     }
    
    # def _escape_string(self, token):
    #     return re.sub(r"[^a-zA-Z0-9]+", '', token)

    # def _process_raw(self, token, last):
    #     token = self._escape_string(token)
    #     return {
    #         "type": "raw",
    #         "piece": token + "/",
    #         "last": token + "/?"
    #     }

    # def _process_single(self, token, last):
    #     name = token[1:]
    #     return {
    #         "type": 'single', 
    #         "name": name,
    #         "piece": "([^/#+]+/)",
	# 	    "last": "([^/#+]+/?)"
    #     }

    # def _tokenize(self, topic):
    #     return topic.split("/")

    # def matches(self):
    #     if "#" not in a_filter and "+" not in a_filter:
    #         return 