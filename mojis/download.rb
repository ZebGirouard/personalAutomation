require 'httparty'
require 'json'
file = File.read('./codecademy-1.json')
data_hash = JSON.parse(file)

data_hash['emoji'].each do |emoji|
  url = emoji['url']
  extension = url.split('.').last
  filename = "codecademy/#{emoji['name']}.#{extension}"
  File.open(filename, "w") do |img_file|
    img_file.binmode
    HTTParty.get(url, stream_body: true) do |fragment|
      img_file.write(fragment)
    end
  end
end