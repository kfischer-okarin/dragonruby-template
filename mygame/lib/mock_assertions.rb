require 'lib/assertions'

module GTK
  class Assert
    def was_called!(mock, method_name, message = nil)
      return ok! unless mock.method_calls(method_name).empty?

      fail_with_message message, "Expected method call #{method_name.inspect}, but it was not called"
    end

    def was_not_called!(mock, method_name, message = nil)
      return ok! if mock.method_calls(method_name).empty?

      fail_with_message message, "Expected not method call #{method_name.inspect}, but it was called"
    end

    def received_call!(mock, method_name, args, kwargs = nil, message = nil)
      kwargs ||= {}
      if args.is_a? Hash
        kwargs = args
        args = []
      end
      message = args if args.is_a? String
      message = kwargs if kwargs.is_a? String

      calls = mock.method_calls(method_name)
      expected_call = [args, kwargs]
      return ok! if calls.include?([args, kwargs])

      fail_with_message message, <<~ERROR
        Expected calls:
        #{safe_format(calls)}

        to include:

        #{expected_call.inspect}
      ERROR
    end
  end
end
