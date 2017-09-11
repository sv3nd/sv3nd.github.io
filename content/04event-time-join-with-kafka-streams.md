Title: Event time join with Kafka Streams
Date: 2017-09-13
Tags: kafka, kafka-streams, stream-processing
Author: Svend Vanderveken


joining a stream of user events with a stream of user metadata, both potentially subject to out of order delivery events.


Flink has posted a tutorial where, as far as I understand, the result is correct and deterministic as long as out of order events are not received after the watermark. 

http://training.data-artisans.com/exercises/eventTimeJoin.html



principle 

https://github.com/dataArtisans/flink-training-exercises/blob/master/src/main/scala/com/dataartisans/flinktraining/exercises/datastream_scala/lowlatencyjoin/EventTimeJoinHelper.scala


Also, the API gives us access to the previously joined value, so we can take corrective actions. Like, if the Alice's click had been previously joined and a (europe, +1), now that we know Alice is reallly in Africa, we can emit (Europe, -1), (Africa, +1).


=> the result is a Revision log: we potentially obtain several success

=> in Kafka: KTable, + handle add an remove :) (next blog...)


# Why not relying on Kafka event-time based processing

Kafka streams provides a couple of handy primitives for designing stream processing based on event time. The principle are explained here ... and provide for example window aggregations where events are assigned to the correct window even in the face of out of order events.


Kafka Streams does not offer out-of-the box event time join. A very close feature is the KStreams to KTable join, where the stream of events is joined with the latest version of the dimension, as explained in this blog and this one

https://www.confluent.io/blog/watermarks-tables-event-time-dataflow-model/

https://www.confluent.io/blog/distributed-real-time-joins-and-aggregations-on-user-activity-events-using-kafka-streams/

Also, because Kafka Streams provides a best-effort flow control: 

http://docs.confluent.io/current/streams/architecture.html?highlight=flow%20control#flow-control-with-timestamps

This KSTreams to KTable join will provide the correctly joined result even in the face of some out of order events (assuming timestamp - link - , are properly set to the events). 

This is already quite powerful and probably exactly what we need in many cases. At the time of writting this, this is already something taht Spark Structure Streaming does not provide out of the box, since it allows only join to static data. 


However, But the "lookup" is only done on processing time and we only , => to fully support event-time-join of out of order streams, we need to manually keep some buffers of both streams,  




# High level approach 

This is almost exactly the same as the solution explained in the  the Flink tutorial

The gist of my solution just boils down to: 
- performing a best effort join at the moment the event arrives
- keeping a time-bounded buffer of recent events and dimension info
- on a regular basis, review the previously joined info 

[diagram here: best effort join by looking up info from dim and event buffers]
[diagram here: periodic revisit, by reviewing past data before some watermark]



# Tools of the trade

## Key Kafka Streams components I rely on here: 


- the processor API that allow low level access to the events. 

- key-value store, awesome feature of Kafka Streams, these stores are backed by a kafka topic and survive a restart of this instance of the streaming application

- window store: time-bounded key value store. As I understand it these are the stores used primarily for backing the window-based operations, though I use them here as simple key-value store that have a time-to-time for each key. They allow us to store value associated to a key and a timestame, like this: `kv.put(key, value, timesstamp)` and then retrieve all values for this key within a given time range, like this:  `kv.fetch(key, fromTime, toTime)`. Here again they are persistent and survive a restart. 

- listening to several topics at once

## Gotcha: topic partitioning trade-off: consumer distribution vs watermark progress

watch out: punctuate and event time go forward when all partitions do



# The code!

## Test data

```bash
> kafka-topics --create --zookeeper localhost:2181 --topic etj-moods --replication-factor 1 --partitions 4
> kafka-topics --create --zookeeper localhost:2181 --topic etj-events --replication-factor 1 --partitions 4
Created topic "etj-events".
```


=> you can check that have been posted to kafka as follows: 
kafka-console-consumer --bootstrap-server localhost:9092 --topic etj-moods --from-beginning


kafka-console-consumer --bootstrap-server localhost:9092 --topic etj-events --from-beginning



start them togheter so produced timestamps are similar and kafka stream is able to apply flow control [link]

Since Kafka is persistent we're using it more as a storage than as a communication channel here


note that the implementation assumes that the messages and already partitioned by user. Note that the .selectKey followed by the .transform does _NOT_ trigger a repartitioning ^^

```python
kafka_producer.send(
    topic=target_topic, 
    value=event_json,
    key=event["consultant"].encode("UTF-8"),
    timestamp_ms=event_time_1970(event["event_time"]))
```


## Kafka Stream event-time join

...


# Conclusion

I love the Kafka Streams abstractions, the duality between logs and tables is present a bit everywhere and offer a refreshing way of designing processing. 

I like less the current API, mostly java-based and OO-based, it encourages mutating objects and does not make it easy to write elegant scala constructions. Hopefully a functional-oriented and scala based API will be offered at some point in the future (pretty please?) 


