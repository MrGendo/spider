import hashlib
from datetime import datetime

import redis
from scrapy_redis_bloomfilter.bloomfilter import BloomFilter

from venus.settings import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PARAMS, BLOOMFILTER_BIT, BLOOMFILTER_HASH_NUMBER


class RedisTool:
    """
        Redis操作工具类，提供Bloom Filter和Cookie管理等功能。
    """
    BF_PREFIXES = {
        "goods": "bloom_filter_goods",
        "post": "bloom_filter_post",
        "user": "bloom_filter_user",
        "img": "bloom_filter_img",
        "attach": "bloom_filter_attach",
    }
    _strict_redis = None

    def __new__(cls, *args, **kwargs):
        if not cls._strict_redis:
            print('new _strict_redis')
            pool = redis.ConnectionPool(host=REDIS_HOST, password=REDIS_PARAMS.get('password'), port=REDIS_PORT,
                                        db=REDIS_DB)
            cls._strict_redis = redis.StrictRedis(connection_pool=pool)
            # 使用循环和BF_PREFIXES字典来初始化Bloom Filter，减少重复代码
            for prefix, name in RedisTool.BF_PREFIXES.items():
                setattr(RedisTool, f"bf_{prefix}",
                        BloomFilter(RedisTool._strict_redis, name, BLOOMFILTER_BIT, BLOOMFILTER_HASH_NUMBER))
        return super(RedisTool, cls).__new__(cls)

    def __init__(self):
        self.redis_conn = RedisTool._strict_redis

    def set_cookie(self, spider_name: str, cookie_value, expire_time: int):
        key = f"{spider_name}_cookie"
        try:
            # 使用Pipeline来保证多个命令的原子性
            pipeline = self.redis_conn.pipeline()
            pipeline.hmset(key, cookie_value)  # 使用hmset代替多个hset的循环，提高性能
            if expire_time > 0:
                pipeline.expire(key, expire_time)
            pipeline.execute()
        # except RedisError as e:
        #     print(f"设置cookie时发生Redis错误: {e}")
        except Exception as e:
            print(f"设置cookie时发生未知错误: {e}")

    def get_cookie(self, spider_name: str):
        key = f"{spider_name}_cookie"
        return self.redis_conn.hgetall(key)

    def _bf_exists(self, bloom_filter_attr: str, spider_name: str, *args) -> bool:
        bloom_filter = getattr(self, bloom_filter_attr)
        hash_value = self.hash_function(spider_name, *args)
        return bloom_filter.exists(hash_value)

    def _bf_add(self, bloom_filter_attr: str, spider_name: str, *args):
        bloom_filter = getattr(self, bloom_filter_attr)
        hash_value = self.hash_function(spider_name, *args)
        bloom_filter.insert(hash_value)

    def bf_post_exists(self, spider_name: str, url: str, timestamp) -> bool:
        return self._bf_exists("bf_post", spider_name, url, timestamp)

    def bf_post_add(self, spider_name: str, url: str, timestamp):
        self._bf_add("bf_post", spider_name, url, timestamp)

    def bf_good_exists(self, spider_name: str, url: str) -> bool:
        return self._bf_exists("bf_post", spider_name, url, datetime.today().strftime("%Y-%m-%d"))

    def bf_good_add(self, spider_name: str, url: str):
        self._bf_add("bf_post", spider_name, url, datetime.today().strftime("%Y-%m-%d"))

    def bf_img_exists(self, spider_name: str, img_url: str, img_name: str) -> bool:
        return self._bf_exists("bf_img", spider_name, img_url, img_name)

    def bf_img_add(self, spider_name: str, img_url: str, img_name: str):
        self._bf_add("bf_img", spider_name, img_url, img_name)

    def bf_attach_exists(self, spider_name: str, attach_name: str, attach_url: str) -> bool:
        return self._bf_exists("bf_attach", spider_name, attach_name, attach_url)

    def bf_attach_add(self, spider_name: str, attach_name: str, attach_url: str):
        self._bf_add("bf_attach", spider_name, attach_name, attach_url)

    def bf_user_exists(self, spider_name: str, user_id: str) -> bool:
        return self._bf_exists("bf_user", spider_name, user_id, datetime.today().strftime("%Y-%m-%d"))

    def bf_user_add(self, spider_name: str, user_id: str):
        self._bf_add("bf_user", spider_name, user_id, datetime.today().strftime("%Y-%m-%d"))

    @staticmethod
    def hash_function(spider_name: str, param1: str, param2: str) -> str:
        combined = f"{spider_name}{param1}{param2}"
        # 安全性考虑，使用SHA-256哈希函数而不是MD5
        hash_value = hashlib.sha256(combined.encode()).hexdigest()
        # print(hash_value)
        return hash_value

    def set_total_pages(self, site, total_pages):
        self.redis_conn.set(f"total_pages_{site}", total_pages)

    def get_total_pages(self, site):
        return self.redis_conn.get(f"total_pages_{site}")

    def set_crawled_pages(self, site, crawled_pages):
        self.redis_conn.set(f"crawled_pages_{site}", crawled_pages)

    def get_crawled_pages(self, site):
        return self.redis_conn.get(f"crawled_pages_{site}")

    def remove_fingerprint(self, spider_name: str, fingerprint: str):
        key = f"{spider_name}:dupefilter"
        self.redis_conn.srem(key, fingerprint)



if __name__ == '__main__':
    redis_tool = RedisTool()
    # redis_tool2 = RedisTool()
    # redis_conn1 = redis_tool.get()
    # redis_conn2 = redis_tool2.get()
    # if redis_tool.redis_conn is redis_tool2.redis_conn:
    #     print("same")
    dict_asap = redis_tool.get_cookie("venus")
    print(dict_asap)

    # redis_tool.set_cookie("Onniforums2", dict_onniforum, -1)
    # o2 = redis_tool.get_cookie("Onniforums2")
    # print(o2)
    # redis_tool.bf_user_add("Onniforums2", "userid_123")
    #
    # res = redis_tool2.bf_user_exists("Onniforums2", "userid_123")
    # print(res)
