package com.example.fraud;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.functions.AggregateFunction;
import org.apache.flink.api.common.serialization.SerializationSchema;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.sink.KafkaSink;
import org.apache.flink.connector.kafka.sink.KafkaRecordSerializationSchema;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.windowing.ProcessWindowFunction;
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.flink.streaming.api.windowing.windows.TimeWindow;
import org.apache.flink.util.Collector;

import java.time.Duration;
import java.time.Instant;

public class FraudFeaturesJob {
  static final ObjectMapper MAPPER = new ObjectMapper();

  public static void main(String[] args) throws Exception {
    final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

    String bootstrap = System.getenv().getOrDefault("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092");

    KafkaSource<String> source = KafkaSource.<String>builder()
        .setBootstrapServers(bootstrap)
        .setTopics("transactions")
        .setGroupId("flink-features")
        .setValueOnlyDeserializer(new SimpleStringSchema())
        .build();

    DataStream<String> raw = env.fromSource(
        source,
        WatermarkStrategy.noWatermarks(),
        "kafka-transactions"
    );

    SingleOutputStreamOperator<Transaction> txns = raw.map(json -> MAPPER.readValue(json, Transaction.class));

    // Use event time from ts (ISO string) + 5s out-of-orderness
    WatermarkStrategy<Transaction> wm = WatermarkStrategy
        .<Transaction>forBoundedOutOfOrderness(Duration.ofSeconds(5))
        .withTimestampAssigner((t, ts) -> parseTsMillis(t.ts));

    SingleOutputStreamOperator<TxnFeature> feats =
        txns.assignTimestampsAndWatermarks(wm)
            .keyBy(t -> t.user_id)
            .window(TumblingEventTimeWindows.of(Time.seconds(60)))
            .aggregate(new Agg(), new ToFeature());

    KafkaSink<TxnFeature> sink = KafkaSink.<TxnFeature>builder()
        .setBootstrapServers(bootstrap)
        .setRecordSerializer(
            KafkaRecordSerializationSchema.builder()
                .setTopic("txn_features")
                .setValueSerializationSchema((SerializationSchema<TxnFeature>) element ->
                    MAPPER.writeValueAsBytes(element)
                )
                .build()
        )
        .build();

    feats.sinkTo(sink);

    env.execute("Fraud Features Job");
  }

  static long parseTsMillis(String iso) {
    if (iso == null || iso.isEmpty()) return Instant.now().toEpochMilli();
    return Instant.parse(iso).toEpochMilli();
  }

  // accumulator: (count, sum)
  public static class Acc {
    public long count = 0;
    public double sum = 0.0;
  }

  public static class Agg implements AggregateFunction<Transaction, Acc, Acc> {
    @Override public Acc createAccumulator() { return new Acc(); }

    @Override
    public Acc add(Transaction value, Acc acc) {
      acc.count += 1;
      acc.sum += value.amount;
      return acc;
    }

    @Override public Acc getResult(Acc acc) { return acc; }

    @Override
    public Acc merge(Acc a, Acc b) {
      Acc m = new Acc();
      m.count = a.count + b.count;
      m.sum = a.sum + b.sum;
      return m;
    }
  }

  public static class ToFeature extends ProcessWindowFunction<Acc, TxnFeature, String, TimeWindow> {
    @Override
    public void process(String key, Context ctx, Iterable<Acc> elements, Collector<TxnFeature> out) {
      Acc acc = elements.iterator().next();
      TxnFeature f = new TxnFeature();
      f.user_id = key;
      f.window_end_epoch_ms = ctx.window().getEnd();
      f.txn_count_60s = acc.count;
      f.total_amount_60s = acc.sum;
      f.avg_amount_60s = (acc.count == 0) ? 0.0 : (acc.sum / acc.count);
      out.collect(f);
    }
  }
}
