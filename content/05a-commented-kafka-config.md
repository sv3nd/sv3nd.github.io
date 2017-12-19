Title: A commented Kafka configuration
Date: 2017-12-19
Tags: kafka
Author: Svend Vanderveken

Diving into Kafka configuration is a beautiful journey into its features. 

As a preparation for a production deployment of Kafka 0.11, I gathered a set of comments on what I think are some interesting parameters. All this amazing wisdom is mostly extracted from the few resources mentioned at the end of this post. 

### A grain of salt...

This is all for information only, I honestly think most of the points below are relevant and correct, though mistakes and omissions are likely present here and there. 

You should not apply any of this blindly to your production environment and hope for anything to work. 

The wiser thing to do _of course_ is renting my services, I'm freelance, see my contact references beside :)  

### Broker basic parameters

Let's start with a few comments on Kafka broker basic parameters, maybe located somewhere like `etc/kafka/server.properties`

First off, each broker must know its enpoint as known by consumers and producers. This is because a Kafka cluster keeps a dynamic list of which broker serves which topic partition. Consumers and producers then obtain that routing information as part of the topic metadata and connect directly to the appropriate broker when exchanging data. 

```
listeners=PLAINTEXT://your.host.name:9092
```

Next, it's a good idea to specify a `chroot` folder in the zookeeper connection string to keep the future flexibility of sharing it with other tools or even another Kafka cluster. Recall that several Kafka brokers are considered to be part of the same cluster if they share the same location on a zookeeper ensemble. Zookeeper is super sensible to load and access latency, so sharing it betweeen many frameworks is not always a good idea.

```
zookeeper.connect=zookeeper1:2181,zookeeper2:2181,zookeeper3:2181/kafka
```

While we're on the subject of zookeeper, the two following can be handy. Note that setting a long timeout is not a magic solution to latency issues since it makes the detection and resolution of crashed brokers slower.

```
zookeeper.connection.timeout.ms=6000
zookeeper.session.timeout.ms=6000
```

The broker log location can be specified as a comma-separated list of mount points. For higher throughput, one can specify several disks here.

```
log.dirs=/some/location,/some/other-location-on-another-disk
```

The following parameter specifies the number of threads used during startup and  shut-down for cleaning up logs and getting to a stable state. Since they are only used at that moment, increasing it may speedup startup time (especially right after a major failure that requires lots' of cleanup) and should otherwise not impact the performance during the rest of the lifetime of the broker.

```
num.recovery.threads.per.data.dir=2
```

In production, I would disable topic auto-creation, to make sure all topics are created with explictly chosen parameters. I would also tend to disable the deletion of topics: 

```
auto.create.topics.enable=false

delete.topic.enable=false
```

Default max message size is 1M. That setting can also be set per topic:

````
# this is overridable at topic creation time with --config max.message.bytes
#message.max.bytes=1000000
````

### Data retention

Log retention is configured by time and/or by size. If both are specified, whichever condition is true first triggers a cleanup. Time-based retention can be specified in `hour`, `minutes` or `ms`, you should only specify one of those time period, though if you specify several, the smallest time granularity takes precedence. 

Logs are sliced into segments of the max size or max duration specified in the last two paremeters below. 

**Gotcha 1**: Kafka is not going to clean up less than a full and past segment. This means that if you have a low traffic topic and set its retention to, say, a couple of hours, data might still take days to be cleaned up since we need to fill up a segment before cleaning it up.

**Gotach 2**: relying on `log.segment.ms` implies that segments of all topic partitions are going to be rolled at approximatively the same moment, which might impact all broker sensibly of you have lot's of partitions and data.


```sh
# this can be overriden at topic creation time with --config retention.ms
log.retention.hours=168

# this can be overriden at topic creation time with --config retention.bytes
log.retention.bytes=1073741824

# this is overridable at topic creation time with --config segment.bytes 
log.segment.bytes=268435456

# this is overridable at topic creation time with --config segment.ms
log.segment.ms=123456
```

Consumer have their offsets committed in Kafka now (except if your client handles them explicitly in some other way), so they are also subject to retention. The default is 1 day. If you have a low traffic topic that might receive less than one message per day, your consumers offsets would not get updated and could be removed from Kafka. Setting `offsets.retention.minutes` to a higher value should help in such case. 

```
# keep consumer offset for two weeks
offsets.retention.minutes=20160
```

### Broker data availability parameters

If a topic is replicated, all read and write operations are performed on the leader partition and all other replicas are just slave copies. Such slave replica is said to be "out-of-sync" if it lags behind the latest records available in its leader. 

In case the leader crashes at a moment when all live replicas are out-of-sync, Kafka will by default not allow such "unclean" replicas to become the new leader since data could be lost and/or consumers could be confused about offset fuzzy business. If you would like to favour availability over data consistency, you can choose to allow such "unclean leader election". Note that you can specify this per topic as well. 

```
# this is overridable at topic creation time with --config unclean.leader.election.enable
unclean.leader.election.enable=false
```

The following parameter is a similar availabiliy vs consistency tradeoff: data producers have the possibility to request that "all" partition replicas confirm the reception of a record before considering the write operation as successful (cf `acks` parameter below). In case some replicas are known to be out-of-sync, we know they are not going to provide such acknowledgment at the moment. The parameter below specifies the minimum number of replicas that must still be in sync such that we can consider that "all" replicas have confirmed the reception of a record.

```
# this is overridable at topic creation time with --config min.insync.replicas
min.insync.replicas=2
```

### Kafka producers

Kafka producers and consumer are rich clients that are packed with features like batching, message routing, compression, retries... and all that gets to be parameterized as well :) 

One key piece of information to keep in mind is that configuring producers and consumers makes sense when we code directly against their API, **as well when we want to configure Kafka Connect, Kafka Stream, Flink Kafka connector, Spark Kafka connector and pretty much any java or scala component that relies on them**, simply because, well, all their features still matter once they're wrapped in such tools.  


#### Basic parameters

`bootstrap.servers` should specify a couple of kafka brokers. If at least one of them is still valid at the moment the connection happens, the client will then rely on Kafka service discovery to figure out all the others. 

```
bootstrap.servers=some-broker:9092.some-other-broker:9092
```

Pretty much all a broker knows about a record payload is that it's a key/value pair made of bytes. Serializers are used by the producer to convert java instances to such byte arrays. One possible choice here is to rely on [Confluent's avro / schema registry serializer](https://github.com/confluentinc/schema-registry/blob/3.3.1-post/avro-serializer/src/main/java/io/confluent/kafka/serializers/KafkaAvroSerializer.java) to obtain avro records with a schema properly declared and versioned in the Conluent schema registry.

```
value.serializer=some.class

key.serializer=some.class
```

Producers also optionally handle data compression for us. For maximum throughput, there is a tradeoff to be experimentally found between message size and cpu time spent (de)compressing it.

```
# compression codec. 
# "none", "snappy", "lz4" or "gzip"
compression.type=lz4

```

The following controls the maximum amount of time the client will wait for the response of a request.

```
request.timeout.ms=30000
```

#### Delivery guaranties

Kafka producers perform retries for us! As many as we want. The `retries` parameter specifies the maximum amount of retries that will be attempted on a retry-able error (like, leader not available) and `retry.backoff.ms` specifies how long to wait between each attempt. 

Note that as the producer keep on retrying while potentially also trying to send new traffic, pending messages can quickly occupy some space, so make sure `buffer.memory` is set properly. Finally, once the memory buffer is full (or if topic metadata are impossible to obtain at the moment), the producer will block during `max.block.ms` before blowing up. 

I guess this is Kafka's take on back-pressure. 

Really, if we care about data consistency, and assuming all upstreams components are behaving accordingly, blocking might be the best thing to do here. Well, blowing up might also be the way. Each case should be designed. 


```
# this default to 0, unless you enabled idempotence
retries=2147483647

retry.backoff.ms=100

buffer.memory=33554432

max.block.ms=60000
```

As mentioned above on the section `min.insync.replica`, producer can specify the amount of required acknowledgments for a write to be considered successful. 


```
# this defaults to 1, unless you enabled idempotence
acks=all
```

Idempotent producers is one of the awesome feature that Kafka folks gifted to the world in version 0.11. That is a long subject, though in a nutshell it guarantees that successfully written records are written exactly once to the brokers. Previously, due to some corner cases in the retry mechanism, some message could have ended-up being duplicated. 

```
# Idempotent retries features of Kafka, introduced in 0.11, 
# Part of components enabing Kafka Streams exactly-once processing semantics.
enable.idempotence=false
```


#### Output record batching 

Kafka producers also automatically batch our records together and send them asynchronously!

In case enough data is available when the producer sends data, it will pack them per batch of `batch.size` bytes. If less data is available it just sends what it has without waiting, unless `linger.ms` is set to a positive value, in which case it waits a bit to get a chance to pack a few more: 

```
batch.size=16384

linger.ms=0
```

By default, the producer will wait for a batch to be acknowledged, as specified by `acks` above, before sending the next batch. For potentially faster throughput, we set the following parameter to some value greater than one to specify the maximum amount of such un-acknowledged batches that we allow.

**Gotcha**: setting this to anything else than 1 destroys the per-topic ordering guarantee of Kafka, simply because some in-flight batches might fail and be retried, while others might go through, in any order.

```
# If set enable.idempotence to true, it may not be greater than 5
#max.in.flight.requests.per.connection=1
```

### Kafka consummers 


#### Basic parameters

Kafka consumer group share the read load when reading from topics. 

```
group.id="my client"
```

See producer discussion regarding broker endpoint and serialisers


```
bootstrap.servers=some-broker:9092.some-other-broker:9092

value.deserializer=some.class

key.deserializer=some.class
```

`fetch.min.bytes=1` means the consumer will start reading as early as at least one message of at least one byte is available. Forcing higher values here might lead to reading by larger chunks and relying on less network round trips. 

In a similar fashion, `max.poll.records` specifies, well, the maximum number of message to fetch each time. 

```
fetch.min.bytes=1

max.poll.records=500
```

The following specifies where to start reading a topic when a consumer appears and does not have a previous offset to start from. This is the typical situation that happens when a new consumer group is created, although it can also be relevant if that offset existed in the past but disappeared due to the `offsets.retention.minutes` parameter mentioned above. `latest` will make the consumer tail the log while `earliest` will (re)-start from the beginning.

```
auto.offset.reset=earliest
```

Consumer offsets get committed by default to a Kafka topics. That is a reasonnable default, though sometimes you might prefer to handle them yourself. For example this [blog post by Guru Medasani shows how to commit offsets with the processed data in Hbase](http://blog.cloudera.com/blog/2017/06/offset-management-for-apache-kafka-with-apache-spark-streaming/).

```
enable.auto.commit=true
```

#### Group robustness and record delivery guarantees

A consumer instance needs to be considered alive to remain part of a consumer group. If it fails to emit hearbeats for more than `session.timeout.ms`, it gets kicked out and a group rebalance happens. 

```
heartbeat.interval.ms=3000

session.timeout.ms=10000
```


The Kafka consumer refreshes its knowledge of the metadata describing a topic at fixed interval, as defined below. Little known fact: if your consomer start consuming from a topic _before you create it_ (it's not going to consumme much, is it?), maybe because some consuming client got deployed a bit too early, it will block, then retry discovering the location of the relevant partition after that period as well. 


```
metadata.max.age.ms=300000
```


Kafka 0.11 introduced so-called _transactions_. Essentially, they try to mimic the _read committed_ isolation feature of ACID transactions by allowing a producer to mark a set of written records, typically accross several topics, as part of the same atomic write operation. Kafka consumer will ignore that feature by default, unless they are configured with `isolation.level=read.committed`, in which case any record that is not part of a committed transaction gets discarded. 

Note that this does **not** achieves atomic read: this is an all-or-nothing _write_ operation: from the read side, there is no way to have an all-or-nothing mechanism. 

```
isolation.level=read_uncommitted
```


# Sources: 

Most of the content above has been heavily inspired from the book chapters and blog posts below.

Kafka, the definitive guide - Gwen Shapira, Todd Palino,  Neha Narkhede:

  * [chapter 2: installing Kafka](https://www.safaribooksonline.com/library/view/kafka-the-definitive/9781491936153/ch02.html#installing_kafka)
  * [chapter 3: Kafka producers](https://www.safaribooksonline.com/library/view/kafka-the-definitive/9781491936153/ch03.html#writing_messages_to_kafka)
  * [chapter 4: Kafka consumers](https://www.safaribooksonline.com/library/view/kafka-the-definitive/9781491936153/ch04.html)
  * [chapter 6: Reliable data delivery](https://www.safaribooksonline.com/library/view/kafka-the-definitive/9781491936153/ch06.html#reliable_data_delivery)


[Apache Kafka setup series, Kafka setup and administration (Udemy class) - Stephane Maarek](https://www.udemy.com/apache-kafka-series-setup-administration-in-production/)

Confluent blog: 

  - [Exactly-once Semantics are Possible: Here’s How Kafka Does it - Neha Narkhede](https://www.confluent.io/blog/exactly-once-semantics-are-possible-heres-how-apache-kafka-does-it)
  - [Transactions in Apache Kafka - Apurva Mehta, Jason Gustafson](https://www.confluent.io/blog/transactions-apache-kafka/)

[Kafka configuration documentation on kafka.org](http://kafka.apache.org/documentation/#configuration)

[Kafka producer Javadoc](https://kafka.apache.org/0110/javadoc/index.html?org/apache/kafka/clients/producer/KafkaProducer.html)

[Configuring High Availability and Consistency for Kafka | 3.0.x | Cloudera Documentation](https://www.cloudera.com/documentation/kafka/latest/topics/kafka_ha.html)



