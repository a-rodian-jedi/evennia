"""
Unit tests for typeclass base system

"""
from django.test import override_settings
from evennia.utils.test_resources import BaseEvenniaTest
from evennia.typeclasses import attributes
from mock import patch
from parameterized import parameterized

# ------------------------------------------------------------
# Manager tests
# ------------------------------------------------------------


class TestAttributes(BaseEvenniaTest):
    def test_attrhandler(self):
        key = "testattr"
        value = "test attr value "
        self.obj1.attributes.add(key, value)
        self.assertEqual(self.obj1.attributes.get(key), value)
        self.obj1.db.testattr = value
        self.assertEqual(self.obj1.db.testattr, value)

    @override_settings(TYPECLASS_AGGRESSIVE_CACHE=False)
    @patch("evennia.typeclasses.attributes._TYPECLASS_AGGRESSIVE_CACHE", False)
    def test_attrhandler_nocache(self):
        key = "testattr"
        value = "test attr value "
        self.obj1.attributes.add(key, value)
        self.assertFalse(self.obj1.attributes.backend._cache)

        self.assertEqual(self.obj1.attributes.get(key), value)
        self.obj1.db.testattr = value
        self.assertEqual(self.obj1.db.testattr, value)
        self.assertFalse(self.obj1.attributes.backend._cache)

    def test_weird_text_save(self):
        "test 'weird' text type (different in py2 vs py3)"
        from django.utils.safestring import SafeText

        key = "test attr 2"
        value = SafeText("test attr value 2")
        self.obj1.attributes.add(key, value)
        self.assertEqual(self.obj1.attributes.get(key), value)

    def test_batch_add(self):
        attrs = [
            ("key1", "value1"),
            ("key2", "value2", "category2"),
            ("key3", "value3"),
            ("key4", "value4", "category4", "attrread:id(1)", False),
        ]
        new_attrs = self.obj1.attributes.batch_add(*attrs)
        attrobj = self.obj1.attributes.get(key="key4", category="category4", return_obj=True)
        self.assertEqual(attrobj.value, "value4")
        self.assertEqual(attrobj.category, "category4")
        self.assertEqual(attrobj.locks.all(), ["attrread:id(1)"])


class TestTypedObjectManager(BaseEvenniaTest):
    def _manager(self, methodname, *args, **kwargs):
        return list(getattr(self.obj1.__class__.objects, methodname)(*args, **kwargs))

    def test_get_by_tag_no_category(self):
        self.obj1.tags.add("tag1")
        self.obj1.tags.add("tag2")
        self.obj1.tags.add("tag2c")
        self.obj2.tags.add("tag2")
        self.obj2.tags.add("tag2a")
        self.obj2.tags.add("tag2b")
        self.obj2.tags.add("tag3 with spaces")
        self.obj2.tags.add("tag4")
        self.obj2.tags.add("tag2c")
        self.assertEqual(self._manager("get_by_tag", "tag1"), [self.obj1])
        self.assertEqual(set(self._manager("get_by_tag", "tag2")), set([self.obj1, self.obj2]))
        self.assertEqual(self._manager("get_by_tag", "tag2a"), [self.obj2])
        self.assertEqual(self._manager("get_by_tag", "tag3 with spaces"), [self.obj2])
        self.assertEqual(self._manager("get_by_tag", ["tag2a", "tag2b"]), [self.obj2])
        self.assertEqual(self._manager("get_by_tag", ["tag2a", "tag1"]), [])
        self.assertEqual(self._manager("get_by_tag", ["tag2a", "tag4", "tag2c"]), [self.obj2])

    def test_get_by_tag_and_category(self):
        self.obj1.tags.add("tag5", "category1")
        self.obj1.tags.add("tag6")
        self.obj1.tags.add("tag7", "category1")
        self.obj1.tags.add("tag6", "category3")
        self.obj1.tags.add("tag7", "category4")
        self.obj2.tags.add("tag5", "category1")
        self.obj2.tags.add("tag5", "category2")
        self.obj2.tags.add("tag6", "category3")
        self.obj2.tags.add("tag7", "category1")
        self.obj2.tags.add("tag7", "category5")
        self.obj1.tags.add("tag8", "category6")
        self.obj2.tags.add("tag9", "category6")

        self.assertEqual(self._manager("get_by_tag", "tag5", "category1"), [self.obj1, self.obj2])
        self.assertEqual(self._manager("get_by_tag", "tag6", "category1"), [])
        self.assertEqual(self._manager("get_by_tag", "tag6", "category3"), [self.obj1, self.obj2])
        self.assertEqual(
            self._manager("get_by_tag", ["tag5", "tag6"], ["category1", "category3"]),
            [self.obj1, self.obj2],
        )
        self.assertEqual(
            self._manager("get_by_tag", ["tag5", "tag7"], "category1"),
            [self.obj1, self.obj2],
        )
        self.assertEqual(self._manager("get_by_tag", category="category1"), [self.obj1, self.obj2])
        self.assertEqual(self._manager("get_by_tag", category="category2"), [self.obj2])
        self.assertEqual(
            self._manager("get_by_tag", category=["category1", "category3"]),
            [self.obj1, self.obj2],
        )
        self.assertEqual(
            self._manager("get_by_tag", category=["category1", "category2"]),
            [self.obj1, self.obj2],
        )
        self.assertEqual(self._manager("get_by_tag", category=["category5", "category4"]), [])
        self.assertEqual(self._manager("get_by_tag", category="category1"), [self.obj1, self.obj2])
        self.assertEqual(self._manager("get_by_tag", category="category6"), [self.obj1, self.obj2])

    def test_get_tag_with_all(self):
        self.obj1.tags.add("tagA", "categoryA")
        self.assertEqual(
            self._manager("get_by_tag", ["tagA", "tagB"], ["categoryA", "categoryB"], match="all"),
            [],
        )

    def test_get_tag_with_any(self):
        self.obj1.tags.add("tagA", "categoryA")
        self.assertEqual(
            self._manager("get_by_tag", ["tagA", "tagB"], ["categoryA", "categoryB"], match="any"),
            [self.obj1],
        )

    def test_get_tag_withnomatch(self):
        self.obj1.tags.add("tagC", "categoryC")
        self.assertEqual(
            self._manager("get_by_tag", ["tagA", "tagB"], ["categoryA", "categoryB"], match="any"),
            [],
        )

    def test_batch_add(self):
        tags = ["tag1", ("tag2", "category2"), "tag3", ("tag4", "category4", "data4")]
        self.obj1.tags.batch_add(*tags)
        self.assertEqual(self.obj1.tags.get("tag1"), "tag1")
        tagobj = self.obj1.tags.get("tag4", category="category4", return_tagobj=True)
        self.assertEqual(tagobj.db_key, "tag4")
        self.assertEqual(tagobj.db_category, "category4")
        self.assertEqual(tagobj.db_data, "data4")


class TestTags(BaseEvenniaTest):
    def test_has_tag_key_only(self):
        self.obj1.tags.add("tagC")
        self.assertTrue(self.obj1.tags.has("tagC"))

    def test_has_tag_key_with_category(self):
        self.obj1.tags.add("tagC", "categoryC")
        self.assertTrue(self.obj1.tags.has("tagC", "categoryC"))

    def test_does_not_have_tag_key_only(self):
        self.obj1.tags.add("tagC")
        self.assertFalse(self.obj1.tags.has("tagD"))

    def test_does_not_have_tag_key_with_category(self):
        self.obj1.tags.add("tagC", "categoryC")
        self.assertFalse(self.obj1.tags.has("tagD", "categoryD"))

    def test_has_tag_category_only(self):
        self.obj1.tags.add("tagC", "categoryC")
        self.assertTrue(self.obj1.tags.has(category="categoryC"))

    def test_does_not_have_tag_category_only(self):
        self.obj1.tags.add("tagC", "categoryC")
        self.assertFalse(self.obj1.tags.has(category="categoryD"))


class TestNickHandler(BaseEvenniaTest):
    """
    Test the nick handler replacement.

    """

    @parameterized.expand(
        [
            # shell syntax
            (
                "gr $1 $2 at $3",
                "emote with a $1 smile, $2 grins at $3.",
                False,
                "gr happy Foo at Bar",
                "emote with a happy smile, Foo grins at Bar.",
            ),
            # regex syntax
            (
                "gr (?P<arg1>.+?) (?P<arg2>.+?) at (?P<arg3>.+?)",
                "emote with a $1 smile, $2 grins at $3.",
                True,
                "gr happy Foo at Bar",
                "emote with a happy smile, Foo grins at Bar.",
            ),
            # channel-style syntax
            (
                "groo $1",
                "channel groo = $1",
                False,
                "groo Hello world",
                "channel groo = Hello world",
            ),
            (
                r"groo\s*?|groo\s+?(?P<arg1>.+?)",
                "channel groo = $1",
                True,
                "groo Hello world",
                "channel groo = Hello world",
            ),
            (
                r"groo\s*?|groo\s+?(?P<arg1>.+?)",
                "channel groo = $1",
                True,
                "groo ",
                "channel groo = ",
            ),
            (
                r"groo\s*?|groo\s*?(?P<arg1>.+?)",
                "channel groo = $1",
                True,
                "groo",
                "channel groo = ",
            ),
            (
                r"groo\s*?|groo\s+?(?P<arg1>.+?)",
                "channel groo = $1",
                True,
                "grooHello world",
                "grooHello world",
            ),  # not matched - this is correct!
            # optional, space-separated arguments
            (
                r"groo\s*?|groo\s+?(?P<arg1>.+?)(?:\s+?(?P<arg2>.+?)){0,1}",
                "channel groo = $1 and $2",
                True,
                "groo Hello World",
                "channel groo = Hello and World",
            ),
            (
                r"groo\s*?|groo\s+?(?P<arg1>.+?)(?:\s+?(?P<arg2>.+?)){0,1}",
                "channel groo = $1 and $2",
                True,
                "groo Hello",
                "channel groo = Hello and ",
            ),
            (
                r"groo\s*?|groo\s+?(?P<arg1>.+?)(?:\s+?(?P<arg2>.+?)){0,1}",
                "channel groo = $1 and $2",
                True,
                "groo",
                "channel groo =  and ",
            ),  # $1/$2 replaced by ''
        ]
    )
    def test_nick_parsing(
        self, pattern, replacement, pattern_is_regex, inp_string, expected_replaced
    ):
        """
        Setting up nick patterns and make sure they replace as expected.

        """
        # from evennia import set_trace;set_trace()
        self.char1.nicks.add(
            pattern, replacement, category="inputline", pattern_is_regex=pattern_is_regex
        )
        actual_replaced = self.char1.nicks.nickreplace(inp_string)

        self.assertEqual(expected_replaced, actual_replaced)
        self.char1.nicks.clear()
