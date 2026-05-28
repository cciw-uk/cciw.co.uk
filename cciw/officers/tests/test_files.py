from cciw.cciwmain.utils import has_path_traversal


def test_has_path_traversal():
    assert not has_path_traversal("foo")
    assert not has_path_traversal("foo/bar")
    assert not has_path_traversal("foo/bar/..")
    assert not has_path_traversal("foo/bar/../baz")
    assert not has_path_traversal("foo/bar/../..")
    assert has_path_traversal("foo/bar/../../..")
    assert has_path_traversal("foo/../..")
    assert has_path_traversal("../")
    assert has_path_traversal("../bar")
