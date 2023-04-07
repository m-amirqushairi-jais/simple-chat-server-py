$(document).ready(function () {
  const socket = io.connect(
    'http://' + document.domain + ':' + location.port
  );
  let username;
  let room;

  // Add a login function to handle user authentication
  function login(username, password) {
    return new Promise((resolve, reject) => {
      $.ajax({
        url: '/login',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
          username: username,
          password: password,
        }),
        success: function (response) {
          resolve(response.access_token);
        },
        error: function (error) {
          reject(error);
        },
      });
    });
  }

  // Update the click event handler for the 'join-room' button
  $('#join-room').click(async function () {
    username = $('#username').val();
    room = $('#room').val();
    let password = prompt('Enter your password:');

    try {
      const token = await login(username, password);
      socket.io.opts.extraHeaders = {
        Authorization: 'Bearer ' + token,
      };

      if (username !== '' && room !== '') {
        socket.emit('join', { username: username, room: room });
        $('#chat').show();
        $('#username').prop('disabled', true);
        $('#room').prop('disabled', true);
        $('#join-room').prop('disabled', true);
      }
    } catch (error) {
      alert('Login failed. Please try again.');
    }
  });

  $('#send-message').click(function () {
    let message = $('#message').val();
    if (message !== '') {
      socket.emit('send_message', { message: message, room: room });
      $('#message').val('');
    }
  });

  socket.on('receive_message', function (data) {
    $('#messages').append(
      '<li><b>' +
        data.username +
        '</b> ' +
        data.timestamp +
        ': ' +
        data.message +
        '</li>'
    );
    $('#messages').scrollTop($('#messages')[0].scrollHeight);
  });

  // Add a register function to handle user registration
  function register(username, password) {
    return new Promise((resolve, reject) => {
      $.ajax({
        url: '/register',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
          username: username,
          password: password,
        }),
        success: function (response) {
          resolve(response);
        },
        error: function (error) {
          reject(error);
        },
      });
    });
  }

  // Add a click event handler for a 'register' button (add this button to your HTML)
  $('#register').click(async function () {
    let username = $('#username').val();
    let password = prompt('Enter your password:');

    try {
      await register(username, password);
      alert(
        'Registration successful. You can now join the chatroom.'
      );
    } catch (error) {
      alert('Registration failed. Please try again.');
    }
  });

  // Add a function to refresh the access token
  function refreshToken(refreshToken) {
    return new Promise((resolve, reject) => {
      $.ajax({
        url: '/refresh',
        method: 'POST',
        beforeSend: function (xhr) {
          xhr.setRequestHeader(
            'Authorization',
            'Bearer ' + refreshToken
          );
        },
        success: function (response) {
          resolve(response.access_token);
        },
        error: function (error) {
          reject(error);
        },
      });
    });
  }

  // Update the click event handler for the 'join-room' button to handle token refreshing
  $('#join-room').click(async function () {
    username = $('#username').val();
    room = $('#room').val();
    let password = prompt('Enter your password:');
    try {
      const { access_token, refresh_token } = await login(
        username,
        password
      );
      socket.io.opts.extraHeaders = {
        Authorization: 'Bearer ' + access_token,
      };

      // Periodically refresh the access token using the refresh token
      setInterval(async () => {
        try {
          const newAccessToken = await refreshToken(refresh_token);
          socket.io.opts.extraHeaders = {
            Authorization: 'Bearer ' + newAccessToken,
          };
        } catch (error) {
          console.error('Failed to refresh access token:', error);
        }
      }, 15 * 60 * 1000); // Refresh the token every 15 minutes

      if (username !== '' && room !== '') {
        socket.emit('join', { username: username, room: room });
        $('#chat').show();
        $('#username').prop('disabled', true);
        $('#room').prop('disabled', true);
        $('#join-room').prop('disabled', true);
      }
    } catch (error) {
      alert('Login failed. Please try again.');
    }
  });

  $('#send-private-message').click(function () {
    let recipient = $('#private-recipient').val();
    let message = $('#private-message').val();
    if (recipient !== '' && message !== '') {
      socket.emit('send_private_message', {
        recipient: recipient,
        message: message,
      });
      $('#private-message').val('');
    }
  });

  socket.on('receive_private_message', function (data) {
    let msg = `<li>${data.timestamp} - <b>Private from ${data.username}</b>: ${data.message}</li>`;
    $('#messages').append(msg);
    window.scrollTo(0, document.body.scrollHeight);
  });

  socket.on('join_room_announcement', function (data) {
    $('#messages').append(
      `<li><i>${data.username} has joined the room.</i></li>`
    );
  });

  socket.on('leave_room_announcement', function (data) {
    $('#messages').append(
      `<li><i>${data.username} has left the room.</i></li>`
    );
  });

  socket.on('chat_history', function (data) {
    $('#messages').empty();
    for (const msg of data) {
      $('#messages').append(
        '<li><b>' +
          msg.username +
          '</b> ' +
          msg.timestamp +
          ': ' +
          msg.message +
          '</li>'
      );
    }
    $('#messages').scrollTop($('#messages')[0].scrollHeight);
  });
});
