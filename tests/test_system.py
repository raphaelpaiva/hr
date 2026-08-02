import numbers

from app.system import get_header_info, get_size


def test_header_info_structure():
  info = get_header_info()
  assert set(info.keys()) == {'load', 'mem_usage', 'disk_usage'}


def test_header_info_values_are_numbers():
  info = get_header_info()
  for key in ('load', 'mem_usage', 'disk_usage'):
    assert isinstance(info[key], numbers.Real)


def test_header_info_percentages_in_range():
  info = get_header_info()
  assert 0 <= info['mem_usage'] <= 100
  assert 0 <= info['disk_usage'] <= 100


def test_get_size():
  assert get_size(0) == '0.00B'
  assert get_size(1024) == '1.00KB'
  assert get_size(1536) == '1.50KB'
  assert get_size(1024 ** 3) == '1.00GB'
