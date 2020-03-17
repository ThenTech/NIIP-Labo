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
        elif len(self.pattern) > 1:
            # Test wildcard locations for conformity
            # [MQTT-4.7.1-1], [MQTT-4.7.1-2], [MQTT-4.7.1-3]
            length = len(self.pattern)

            for i in range(length):
                if self.pattern[i] == TopicMatcher.PLUS:
                    if i < length - 1 and not self.pattern[i+1] == TopicMatcher.SEP:
                        raise MQTTTopicException("Wildcard '{0}' not followed by a '{1}' in {2}!" \
                                    .format(TopicMatcher.PLUS, TopicMatcher.SEP, self.pattern))
                    elif i > 0 and not self.pattern[i-1] == TopicMatcher.SEP:
                        raise MQTTTopicException("Wildcard '{0}' not preceded a '{1}' in {2}!" \
                                    .format(TopicMatcher.PLUS, TopicMatcher.SEP, self.pattern))
                elif self.pattern[i] == TopicMatcher.HASH:
                    if i != length - 1:
                        raise MQTTTopicException("Wildcard '{0}' not at end in '{1}'!" \
                                    .format(TopicMatcher.HASH, self.pattern))
                    elif not self.pattern[i-1] == TopicMatcher.SEP:
                        raise MQTTTopicException("Wildcard '{0}' not preceded a '{1}' in {2}!" \
                                    .format(TopicMatcher.HASH, TopicMatcher.SEP, self.pattern))

        if self.pattern == topic:
            # If exact match
            return True
        elif self.pattern == TopicMatcher.HASH:
            # If subscription is #, match anything, except $
            if topic[0] == TopicMatcher.DOLL:
                # [MQTT-4.7.2-1] Don't match $ topics with wildcard
                return False
            else:
                self.pattern = topic
                return True
        # elif self.pattern[0] == TopicMatcher.DOLL:
        #     # [MQTT-4.7.2-1] Starts with $: match exactly (internal use only)
        #     # return self.pattern == topic
        elif  self.pattern[-1] == TopicMatcher.HASH \
          and TopicMatcher.PLUS not in self.pattern \
          and topic[0] != TopicMatcher.DOLL:
            # Ends with # and no +: match anything before that
            matches = topic.startswith(self.pattern[0:-1])
            if matches: self.pattern = topic
            return matches
        elif  self.pattern[0] in (TopicMatcher.PLUS, TopicMatcher.HASH) \
          and topic[0] == TopicMatcher.DOLL:
            # [MQTT-4.7.2-1] Don't match $ topics with wildcard
            return False

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

        # print("{} ==> {} vs {}".format(self.pattern, expanded_pattern, topic))
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
    from mqtt.colours import *

    class Tester:
        NUMBER_OF_TESTS_PASSED = 0
        NUMBER_OF_TESTS_FAILED = 0

        @staticmethod
        def _report(passed):
            if passed:
                Tester.NUMBER_OF_TESTS_PASSED += 1
            else:
                Tester.NUMBER_OF_TESTS_FAILED += 1

        @staticmethod
        def report():
            total = Tester.NUMBER_OF_TESTS_PASSED + Tester.NUMBER_OF_TESTS_FAILED

            print("\n{} of {} tests completed {}! {}".format(
                Tester.NUMBER_OF_TESTS_PASSED, total,
                style("SUCCESSFULLY", Colours.FG.GREEN),
                "" if Tester.NUMBER_OF_TESTS_FAILED == 0 else \
                    ("{} ".format(Tester.NUMBER_OF_TESTS_FAILED) \
                        + style("WITH FAILURES", Colours.FG.RED))))

        @staticmethod
        def test(sub, topic, result=True):
            matches = TopicMatcher(sub).matches(topic)
            print("{}: {} {} {}".format(
                style("SUCCESS", Colours.FG.GREEN)
                    if bool(matches) == result else \
                style("FAILURE", Colours.FG.RED),
                sub, "==" if result else "!=", topic))
            Tester._report(bool(matches) == result)

        @staticmethod
        def test_except(sub, topic, etype):
            try:
                TopicMatcher(sub).matches(topic)
            except Exception as e:
                ename = type(e).__name__
                print("{}: {} vs {} threw {}: {}".format(
                    style("SUCCESS", Colours.FG.GREEN)
                        if ename == etype.__name__ else \
                    style("FAILURE", Colours.FG.RED),
                    sub, topic, ename, e))
                Tester._report(ename == etype.__name__)
            else:
                if etype:
                    print("{}: {} vs {} did not throw error!".format(
                        style("FAILURE", Colours.FG.RED), sub, topic))
                else:
                    print("{}: {} vs {} did not throw error".format(
                        style("SUCCESS", Colours.FG.GREEN), sub, topic))
                Tester._report(not etype)

    # Tests
    Tester.test("#", "hel/scotty")
    Tester.test("#", "hellow")
    Tester.test("#", "this/+/will/always/match")

    Tester.test("hel/#", "hel/scotty")
    Tester.test("hel/#", "hel/rip")
    Tester.test("hel/#", "hel", False)

    Tester.test("hel/top", "hel/top")
    Tester.test("hel/top", "hel/top/mat", False)
    Tester.test("hel/top/#", "hel/top/mat")

    Tester.test("hel/+/#", "hel/top/mat")
    Tester.test("hel/+/#", "hel/bak/mat")
    Tester.test("hel/+/#", "hel/bak", False)
    Tester.test("hel/+/mat", "hel/bak", False)
    Tester.test("hel/+/mat", "hel/bak/mat")
    Tester.test("hel/+/mat", "hel/ert/mat")
    Tester.test("hel/+/mat", "hel/ert/mat/tes", False)
    Tester.test("hel/+/mat/tes", "hel/ert/mat/tes")
    Tester.test("hel/+/mat/#", "hel/ert/mat/tes")
    Tester.test("hel/+/#", "hel/ert/mat/tes")
    Tester.test("+/+", "/finance")
    Tester.test("/+", "/finance")
    Tester.test("+", "/finance", False)

    Tester.test("#", "$SYS", False)
    Tester.test("+/#", "$SYS/here", False)
    Tester.test("+", "$SYS", False)
    Tester.test("+/here", "$SYS/here", False)
    Tester.test("$SYS/+/#", "$SYS/broker/uptime")
    Tester.test("/topic", "topic", False)

    Tester.test_except("+", "test", None)
    Tester.test_except("+/tennis/#", "test/tennis/match", None)
    Tester.test_except("sport+", "sport/", MQTTTopicException)
    Tester.test_except("sport+/", "sport/", MQTTTopicException)
    Tester.test_except("sport/+/", "sport/", None)
    Tester.test_except("+sport", "sport/", MQTTTopicException)
    Tester.test_except("+/sport", "sport/", None)
    Tester.test_except("sport/+/player1", "sport/match/player1", None)
    Tester.test_except("#", "test", None)
    Tester.test_except("/#", "test", None)
    Tester.test_except("test/#", "test", None)
    Tester.test_except("#/", "test", MQTTTopicException)
    Tester.test_except("#/#", "test", MQTTTopicException)
    Tester.test_except("test/#/gest", "test", MQTTTopicException)
    Tester.test_except("test#", "test", MQTTTopicException)
    Tester.test_except("te#st", "test", MQTTTopicException)
    Tester.test_except("te+st", "test", MQTTTopicException)
    Tester.test_except("test/l+p/#", "test", MQTTTopicException)

    Tester.report()
