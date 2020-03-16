from mqtt.mqtt_exceptions import MQTTTopicException

class TopicMatcher:
    HASH = '#'  # Matches anything (multi level)
    PLUS = '+'  # Matches one thing (single level)
    DOLL = '$'  # Matches internal topics from broker
    SEP  = '/'  # Topic hierarchy

    def __init__(self, pattern):
        self.pattern = pattern

    def matches(self, topic):
        # print("Test: {} == {}".format(self.pattern, topic))

        # check for complete match
        if    TopicMatcher.HASH not in self.pattern \
          and TopicMatcher.PLUS not in self.pattern:
            # If no wildcards, match exactly
            return self.pattern == topic
        elif self.pattern == topic:
            # If exact match
            return True
        elif self.pattern == TopicMatcher.HASH:
            # If subscription is #, match anything
            self.pattern = topic
            return True
        elif self.pattern[0] == TopicMatcher.DOLL:
            # Starts with $: match exactly (internal use only)
            return self.pattern == topic
        elif  self.pattern[-1] == TopicMatcher.HASH \
          and TopicMatcher.PLUS not in self.pattern:
            # Ends with # and no +: match anything before that
            matches = topic.startswith(self.pattern[0:-1])
            if matches: self.pattern = topic
            return matches
        elif  TopicMatcher.HASH in self.pattern \
          and self.pattern[-1] != TopicMatcher.HASH:
            # Wildcard # not at end
            raise MQTTTopicException("Wildcard '{0}' not at end in '{1}'!".format(TopicMatcher.HASH, self.pattern))

        # Else go through hierarchy and fill in wildcards
        expanded_pattern = []
        sub_split = self.pattern.split(TopicMatcher.SEP)
        top_split = topic.split(TopicMatcher.SEP)

        for i, (sub_group, match_group) in enumerate(zip(sub_split, top_split)):
            if sub_group == match_group:
                expanded_pattern.append(sub_group)
            elif sub_group == TopicMatcher.PLUS:
                expanded_pattern.append(match_group)
            elif sub_group == TopicMatcher.HASH:
                expanded_pattern.append(TopicMatcher.SEP.join(top_split[i:]))
                break
            else:
                return False

        expanded_pattern.extend(sub_split[i+1:])
        expanded_pattern = TopicMatcher.SEP.join(expanded_pattern)

        print("{} ==> {} vs {}".format(self.pattern, expanded_pattern, topic))
        self.pattern = expanded_pattern
        return self.matches(topic)

    def filtered(self):
        """
        Filter wildcards: call matches() first to get rid of '+',
        then this will remove trailing '/#'.
        """
        filtered_pattern = self.pattern

        if filtered_pattern[-1] == TopicMatcher.HASH:
             filtered_pattern = filtered_pattern[0:-1]
        if filtered_pattern[-1] == TopicMatcher.SEP:
            filtered_pattern = filtered_pattern[0:-1]

        return filtered_pattern


if __name__ == "__main__":
    def test(sub, topic, result=True):
        matches = TopicMatcher(sub).matches(topic)
        print("{}: {} {} {}".format("SUCCESS" if bool(matches) == result else \
                                    "FAILURE",
                                    sub, "==" if result else "!=", topic))

    # Tests
    test("#", "hel/scotty")
    test("#", "hellow")
    test("#", "this/+/will/always/match")

    test("hel/#", "hel/scotty")
    test("hel/#", "hel/rip")
    test("hel/#", "hel", False)

    test("hel/top", "hel/top")
    test("hel/top", "hel/top/mat", False)
    test("hel/top/#", "hel/top/mat")

    test("hel/+/#", "hel/top/mat")
    test("hel/+/#", "hel/bak/mat")
    test("hel/+/#", "hel/bak", False)
    test("hel/+/mat", "hel/bak", False)
    test("hel/+/mat", "hel/bak/mat")
    test("hel/+/mat", "hel/ert/mat")
    test("hel/+/mat", "hel/ert/mat/tes", False)
    test("hel/+/mat/tes", "hel/ert/mat/tes")
    test("hel/+/mat/#", "hel/ert/mat/tes")
    test("hel/+/#", "hel/ert/mat/tes")
