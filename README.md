# PG Metricus

### INFO

pg_metricus is a script written in Python for sending metrics in the socket (Brubeck aggregator, Graphite, etc.) from NOTIFY channel.

It must be remembered, if a NOTIFY is executed inside a transaction, the notify events are not delivered until and unless the transaction is committed. This is appropriate, since if the transaction is aborted, all the commands within it have had no effect, including NOTIFY. But it can be disconcerting if one is expecting the notification events to be delivered immediately.

If the same channel name is signaled multiple times from the same transaction with identical payload strings, the database server can decide to deliver a single notification only. On the other hand, notifications with distinct payload strings will always be delivered as distinct notifications. Similarly, notifications from different transactions will never get folded into one notification. Except for dropping later instances of duplicate notifications, NOTIFY guarantees that notifications from the same transaction get delivered in the order they were sent. It is also guaranteed that messages from different transactions are delivered in the order in which the transactions committed.

### USAGE

Optional arguments:
```
pg_metricus.py [-h] [-H PG_HOST] [-P PG_PORT] [-D DBNAME] [-U USERNAME]
	           [-W PASSWORD] -A SOCKET_HOST -X SOCKET_PORT -C CHANNEL 
	           [-B] [-E]

-H PG_HOST, --pg_host PG_HOST
-P PG_PORT, --pg_port PG_PORT
-D DBNAME, --dbname DBNAME
-U USERNAME, --username USERNAME
-W PASSWORD, --password PASSWORD
-A SOCKET_HOST, --socket_host SOCKET_HOST
-X SOCKET_PORT, --socket_port SOCKET_PORT
-C CHANNEL, --channel CHANNEL
-B, --start_listen
-E, --stop_listen
```

Crontab
```
* * * * *  pg_metricus.py -H 127.0.0.1 -P 5432 -D base -U user -W pass -A 10.9.5.164 -X 8124 -C test
```

### FORMAT

For Brubeck aggregator:
```plpgsql
select pg_notify('test', format(E'%s.%s:%s|%s\n', 
    metric_path, 
    metric_name, 
    metric_value, 
    metric_type
));
```

For Graphite:
```plpgsql
select pg_notify('test', format(E'%s.%s %s %s \n', 
    metric_path, 
    metric_name, 
    metric_value, 
    extract(epoch from now())::integer
));
```

### EXAMPLE

```plpgsql
do language plpgsql $$
declare
	x1 timestamp;
	x2 timestamp;
	v_val_hstore text;
begin

	x1 = clock_timestamp();

	v_val_hstore = get_val_hstore();

	x2 = clock_timestamp();

	perform pg_notify('test', format(E'%s.%s:%s|%s\n', 
        'db.sql.metric', 
        'get_val_hstore_duration', 
        extract(millisecond from (x2 - x1))::bigint::text, 
        'ms'
    ));

end
$$;
```

### Author

Nikolay Vorobev (nvorobev@avito.ru)

### License

MIT
