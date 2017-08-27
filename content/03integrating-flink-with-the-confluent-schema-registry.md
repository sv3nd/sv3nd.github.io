Title: How to integrate Flink with Confluent's schema registry
Date: 2017-06-30
Tags: flink, avro, kafka
Author: Svend Vanderveken


This post illustrates how to use Confluent's Avro serializer in order to let a Flink program consume and produce avro messages through Kafka while keeping track of the Avro Schemas in Confluent's schema registry. This can be interresting if the messages are pumped into or out of Kafka with Kafka Connect, Kafka Streams, or just with anything else also integrated with the schema registry.

**Warning**: As of now (Aug 2017), it turns out using Confluent's Avro deserializer as explained below is not ideal when deploying to FLink in standalone mode, because of the way caching is impemented on Avro level. More information in [this Confluent PR](https://github.com/confluentinc/schema-registry/pull/509#issuecomment-323143951) as well as in [this FLink JIRA](https://issues.apache.org/jira/browse/FLINK-5633). Hopefully a workaround will be found soon.

This has been written with the following dependencies in mind: 

```scala
libraryDependencies ++= Seq(
  "org.apache.flink" %% "flink-scala" % "1.3.1" % "provided",
  "org.apache.flink" %% "flink-streaming-scala" % "1.3.1" % "provided",
  "org.apache.flink" %% "flink-connector-kafka-0.10" % "1.3.1",
 
  "io.confluent" % "kafka-avro-serializer" % "3.2.2")
```

## Confluent's schema registry library

Confluent has published their version of an [Avro Serializer](https://github.com/confluentinc/schema-registry/tree/3.2.1-post/avro-serializer) which automatically (and idempotently) registers the Avro schema into the schema registry when performing serialization (as [visible here](https://github.com/confluentinc/schema-registry/blob/3.2.1-post/avro-serializer/src/main/java/io/confluent/kafka/serializers/AbstractKafkaAvroSerializer.java#L72)). The convention they use is simply to declare 2 _subjects_ within the registry for each kafka topic, called _<topic-name\>-value_ and _<topic-name\>-key_ and put the schema there. This allows the de-serializer to [retrieve the schema when needed](https://github.com/confluentinc/schema-registry/blob/3.2.1-post/avro-serializer/src/main/java/io/confluent/kafka/serializers/AbstractKafkaAvroDeserializer.java#L121).

## Flink Kafka consumer 

There are various aspects to tackle when adding a Kafka consumer as a stream source to Flink. The one we're focusing on here is [the deserializations schema](https://ci.apache.org/projects/flink/flink-docs-release-1.3/dev/connectors/kafka.html#the-deserializationschema). This class is the place where we can specify to Flink how handle the `byte[]` consumed from Kafka, so all we have to do is to plug there Confluent's schema-registry aware Avro deserializer. 

It goes like this: 

```scala
import io.confluent.kafka.serializers.{AbstractKafkaAvroSerDeConfig, KafkaAvroDeserializer}
import org.apache.avro.generic.GenericRecord
import org.apache.flink.api.common.typeinfo.TypeInformation
import org.apache.flink.api.java.typeutils.TypeExtractor
import org.apache.flink.streaming.util.serialization.KeyedDeserializationSchema

case class KafkaKV(key: GenericRecord, value: GenericRecord)

class ConfluentRegistryDeserialization(topic: String, schemaRegistryUrl: String) 
      extends KeyedDeserializationSchema[KafkaKV] {

  // Flink needs the serializer to be serializable => this "@transient lazy val" does the trick
  @transient lazy val valueDeserializer = {
    val deserializer = new KafkaAvroDeserializer()
    deserializer.configure(
      // other schema-registry configuration parameters can be passed, see the configure() code 
      // for details (among other things, schema cache size)
      Map(AbstractKafkaAvroSerDeConfig.SCHEMA_REGISTRY_URL_CONFIG -> schemaRegistryUrl).asJava, 
      false)
    deserializer
  }
  
  @transient lazy val keyDeserializer = {
    val deserializer = new KafkaAvroDeserializer()
    deserializer.configure(
      Map(AbstractKafkaAvroSerDeConfig.SCHEMA_REGISTRY_URL_CONFIG -> schemaRegistryUrl).asJava, 
      true)
    deserializer
  }

  override def isEndOfStream(nextElement: KafkaKV): Boolean = false

  override def deserialize(messageKey: Array[Byte], message: Array[Byte], 
                           topic: String, partition: Int, offset: Long): KafkaKV = {
  
    val key = keyDeserializer(topic, messageKey).asInstanceOf[GenericRecord]
    val value = valueDeserializer.deserialize(topic, message).asInstanceOf[GenericRecord]
    
    KafkaKV(key, value)
  }

  override def getProducedType: TypeInformation[KafkaKV] = 
      TypeExtractor.getForClass(classOf[KafkaKV])
}
```

Once this is in place, we can use it to create a Flink Kafka source as follows: 

```scala
  import org.apache.flink.api.scala._
  import org.apache.flink.streaming.api.scala.StreamExecutionEnvironment
  import org.apache.flink.streaming.connectors.kafka.FlinkKafkaConsumer010
  
  [...]

  val env = StreamExecutionEnvironment.getExecutionEnvironment
  
  val kafkaConsumerConfig = ...

  val kafkaStream = env
    .addSource(
      new FlinkKafkaConsumer010[KafkaKV](
        "someInboundTopic",
        new ConfluentRegistryDeserialization("someInboundTopic", "http://localhost:8081"),
        kafkaConsumerConfig
        )
      )
    )

```

## Flink Kafka producer

This is exactly the same story: in order to be able to produce avro messages into Kafka with Flink while automatically registering their schema in the registry, all we have to do is provide a Flink serializer that is essentially an adapter to Confluent's Avro serializer. 


```scala
type KafkaKey = String
case class SomePojo(foo: String, bar: String)

class ConfluentRegistrySerialization(topic: String, schemaRegistryUrl: String) 
        extends KeyedSerializationSchema[(KafkaKey, SomePojo)]{

  @transient lazy val valueSerializer = {
    val serializer = new KafkaAvroSerializer()
    serializer.configure(
      Map(AbstractKafkaAvroSerDeConfig.SCHEMA_REGISTRY_URL_CONFIG -> schemaRegistryUrl).asJava,
      false)
    serializer
  }

  @transient lazy val keySerializer = {
    val serializer = new KafkaAvroSerializer()
    serializer.configure(
      Map(AbstractKafkaAvroSerDeConfig.SCHEMA_REGISTRY_URL_CONFIG -> schemaRegistryUrl).asJava,
      true)
    serializer
  }

  override def serializeKey(keyedMessages: (KafkaKey, SomePojo)): Array[Byte] =
    keySerializer.serialize(topic, keyedMessages._1)

  override def getTargetTopic(element: (KafkaKey, SomePojo)): String = topic

  override def serializeValue(keyedMessages: (KafkaKey, SomePojo)): Array[Byte] =
     valueSerializer.serialize(topic, keyedMessages._2)
}
```

And again, once this serialization adapter is there, all we have to do is 

```scala
  val kafkaProducerConfig = ...
  
  val someStream = kafkaStream.map(blabla)...

  FlinkKafkaProducer010.writeToKafkaWithTimestamps(
    someStream.javaStream,
    "destinationTopic",
    new AvroRegistrySerialization("destinationTopic", "http://localhost:8081"),
    kafkaProducerConfig)))
```


 That's about it :) 

