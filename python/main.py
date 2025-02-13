from dotenv import load_dotenv
import os
import redis


load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL", "localhost")
REDIS_SET_KEY = "mobydick:words:set"
REDIS_BLOOM_KEY = "mobydick:words:bloom"
REDIS_HLL_KEY = "mobydick:words:hyperloglog"
REDIS_TOPK_KEY = "mobydick:words:topk"

# Create a client and connect to Redis
# Create a pipeline for bulk operations
client = redis.Redis(REDIS_URL)
pipe = client.pipeline()

# Clean up from any previous run...

pipe.delete(REDIS_SET_KEY)
pipe.delete(REDIS_BLOOM_KEY)
pipe.delete(REDIS_HLL_KEY)
pipe.delete(REDIS_TOPK_KEY)

# Initialize Bloom Filter and Top K.

bloom_filter = pipe.bf()
bloom_filter.create(REDIS_BLOOM_KEY, 0.01, 20000)

top_k = pipe.topk()
top_k.reserve(REDIS_TOPK_KEY, 10, 8, 7, 0.9)

# Process the file of words.

with open("../moby_dick_just_words.txt", "r") as fi:
    for line in fi:
        for raw_word in line.split():
            word = raw_word.strip().lower()
            bloom_filter.add(REDIS_BLOOM_KEY, word)
            pipe.sadd(REDIS_SET_KEY, word)
            pipe.pfadd(REDIS_HLL_KEY, word)
            top_k.add(REDIS_TOPK_KEY, word)
            print(word)

# Execute the commands in pipeline
pipe.execute()

# Get some stats...

print(f"There are {client.scard(REDIS_SET_KEY)} distinct words in the Redis Set.")
print(f"The Redis Set uses {client.memory_usage(REDIS_SET_KEY) / 1024}kb of memory.")
print(f"The Redis Hyperloglog counted {client.pfcount(REDIS_HLL_KEY)} distinct words.")
print(
    f"The Redis Hyperloglog uses {client.memory_usage(REDIS_HLL_KEY) / 1024}kb of memory."
)
print(
    f"The Redis Bloom Filter uses {client.memory_usage(REDIS_BLOOM_KEY) / 1024}kb of memory."
)
print(f"The top 10 words are:")
print()

top_k.list(REDIS_TOPK_KEY, withcount=True)
pipe_result = pipe.execute()
top_k_list = pipe_result[-1]

words = top_k_list[::2]
freq = top_k_list[1::2]

frequency_dict = dict(zip(words, freq))

print(frequency_dict)

# Release Redis connection.

client.close()
