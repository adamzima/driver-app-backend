require 'rubygems'
require 'websocket-client-simple'
require 'json'

ws = WebSocket::Client::Simple.connect 'http://0.0.0.0:8080'

ws.on :message do |msg|
  puts msg.data
end

ws.on :open do
  ws.send({message: 'hello!!!'}.to_json)
end

ws.on :close do |e|
  p e
  exit 1
end

ws.on :error do |e|
  p e
end

loop do
  ws.send({message: STDIN.gets.strip}.to_json)
end