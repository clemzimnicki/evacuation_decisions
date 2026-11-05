/**
 * jspsych-image-keyboard-response
 * Josh de Leeuw
 *
 * plugin for displaying a stimulus and getting a keyboard response
 *
 * documentation: docs.jspsych.org
 *
 **/


 var jsPsychImageTextResponseMAS = (function (jspsych) {

  //var plugin = {};

  //jsPsych.pluginAPI.registerPreload('image-text-responseMAS', 'stimulus', 'image');

const info = {
    name: 'image-text-responseMAS',
    description: '',
    parameters: {
      stimulus: {
        type: jspsych.ParameterType.IMAGE,
        pretty_name: 'Stimulus',
        default: undefined,
        description: 'The image to be displayed'
      },
      stimulus_height: {
        type: jspsych.ParameterType.INT,
        pretty_name: 'Image height',
        default: null,
        description: 'Set the image height in pixels'
      },
      stimulus_width: {
        type: jspsych.ParameterType.INT,
        pretty_name: 'Image width',
        default: null,
        description: 'Set the image width in pixels'
      },
      maintain_aspect_ratio: {
        type: jspsych.ParameterType.BOOL,
        pretty_name: 'Maintain aspect ratio',
        default: true,
        description: 'Maintain the aspect ratio after setting width or height'
      },
      choices: {
        type: jspsych.ParameterType.KEYCODE,
        array: true,
        pretty_name: 'Choices',
        default: "ALL_KEYS",
        description: 'The keys the subject is allowed to press to respond to the stimulus.'
      },
      labels: {
        type: jspsych.ParameterType.HTML_STRING,
        pretty_name:'Labels',
        default: [],
        array: true,
        description: 'Labels of image.',
      },
      prompt: {
        type: jspsych.ParameterType.STRING,
        pretty_name: 'Prompt',
        default: null,
        description: 'Any content here will be displayed below the stimulus.'
      },
      prompt_location: {
        type: jspsych.ParameterType.SELECT,
        pretty_name: 'Prompt location',
        options: ['above','below'],
        default: 'above',
        description: 'Indicates whether to show prompt "above" or "below" the sorting area.'
      },
      stimulus_duration: {
        type: jspsych.ParameterType.INT,
        pretty_name: 'Stimulus duration',
        default: null,
        description: 'How long to hide the stimulus.'
      },
      trial_duration: {
        type: jspsych.ParameterType.INT,
        pretty_name: 'Trial duration',
        default: null,
        description: 'How long to show trial before it ends.'
      },
      response_ends_trial: {
        type: jspsych.ParameterType.BOOL,
        pretty_name: 'Response ends trial',
        default: true,
        description: 'If true, trial will end when subject makes a response.'
      },
      trial_type: {
        type: jspsych.ParameterType.SELECT,
        pretty_name: 'Part of trial',
        options: ['Present','TextFeed','MotionFeed'],
        default: 'Present',
        description: 'Which set of features to display.'
      },
      correctAnswer: {
        type: jspsych.ParameterType.STRING,
        pretty_name: 'correct answer',
        default: null,
        description: 'correct answer for the given plate'
      },
      questions: {
        type: jspsych.ParameterType.COMPLEX,
        array: true,
        pretty_name: 'Questions',
        default: undefined,
        nested: {
          prompt: {
            type: jspsych.ParameterType.STRING,
            pretty_name: 'Prompt',
            default: undefined,
            description: 'Prompt for the subject to response'
          },
          placeholder: {
            type: jspsych.ParameterType.STRING,
            pretty_name: 'Value',
            default: "",
            description: 'Placeholder text in the textfield.'
          },
          rows: {
            type: jspsych.ParameterType.INT,
            pretty_name: 'Rows',
            default: 1,
            description: 'The number of rows for the response text box.'
          },
          columns: {
            type: jspsych.ParameterType.INT,
            pretty_name: 'Columns',
            default: 40,
            description: 'The number of columns for the response text box.'
          },
          required: {
            type: jspsych.ParameterType.BOOL,
            pretty_name: 'Required',
            default: false,
            description: 'Require a response'
          },
          name: {
            type: jspsych.ParameterType.STRING,
            pretty_name: 'Question Name',
            default: '',
            description: 'Controls the name of data values associated with this question'
          }
        }
      }
    }
  }

  class ImageTextResponseMASPlugin {
    constructor(jsPsych) {
        this.jsPsych = jsPsych;
    }
    trial(display_element, trial) {


  
    var html = "";

     
      // Display labels above figure
       for(var j=0; j < trial.labels.length; j++){
        var width = 50/(trial.labels.length-1);
        //var left_offset = (j * (50 /(trial.labels.length -1))) - (width+10);
        if (j == 0){
          var left_offset = -95;
        }else{
          var left_offset = 90; 
        }
        html += '<div style="display: inline-block; position: relative; left:'+left_offset+'%; text-align: center; width: '+width+'%;">';
        html += '<span style="text-align: center; font-size: 150%;">'+trial.labels[j]+'</span>';
        html += '</div>'
      }

       // add prompt 
       if (trial.prompt !== null && trial.prompt_location == "above") {
         if (trial.trial_type == "Present"){
          html += '<span style="font-size: 30px; color: RGB(88,88,88)">'+trial.prompt+'</span>'
         }
         else if (trial.trial_type == "TextFeed" || trial.trial_type == "MotionFeed" ){
          html += '<span style="font-size: 30px;">'+trial.prompt+'</span>'
         }
       }
      html+= "<p></p>"

    // display stimulus
    if (trial.trial_type == "Present" || trial.trial_type == "TextFeed"){
      html += '<img src="'+trial.stimulus+'" id="jspsych-image-keyboard-response-stimulus" style="';
    }
    else if (trial.trial_type == "MotionFeed" ){
        // Move image underneath the correct species 
        if (trial.species == "FILK" ){
          html += '<img src="'+trial.stimulus+'" id="jspsych-image-keyboard-response-stimulus" class ="jspsych-image-keyboard-response-left"';
        }
        else if (trial.species == "SLUB"){
          html += '<img src="'+trial.stimulus+'" id="jspsych-image-keyboard-response-stimulus" class ="jspsych-image-keyboard-response-right"';
        }
    }
    
    if(trial.stimulus_height !== null){
      html += 'height:'+trial.stimulus_height+'px; '
      if(trial.stimulus_width == null && trial.maintain_aspect_ratio){
        html += 'width: auto; ';
      }
    }
    if(trial.stimulus_width !== null){
      html += 'width:'+trial.stimulus_width+'px; '
      if(trial.stimulus_height == null && trial.maintain_aspect_ratio){
        html += 'height: auto; ';
      }
    }
    
    html +='"></img>';

    /*if (trial.prompt !== null && trial.prompt_location == "below") {
      html += '<span style="font-size: 120%;">'+trial.prompt+'</span>'
    }
    display_element.innerHTML = html;*/
    // start form
    html += '<form id="jspsych-survey-text-form">'

    // generate question order
    var question_order = [];
    for(var i=0; i<trial.questions.length; i++){
      question_order.push(i);
    }
    if(trial.randomize_question_order){
      question_order = jsPsych.randomization.shuffle(question_order);
    }

    // add questions
    for (var i = 0; i < trial.questions.length; i++) {
      var question = trial.questions[question_order[i]];
      var question_index = question_order[i];
      html += '<div id="jspsych-survey-text-'+question_index+'" class="jspsych-survey-text-question" style="margin: 2em 0em;">';
      html += '<p class="jspsych-survey-text">' + question.prompt + '</p>';
      var autofocus = i == 0 ? "autofocus" : "";
      var req = question.required ? "required" : "";
      if(question.rows == 1){
        html += '<input type="text" id="input-'+question_index+'"  name="#jspsych-survey-text-response-' + question_index + '" data-name="'+question.name+'" size="'+question.columns+'" '+autofocus+' '+req+' placeholder="'+question.placeholder+'"></input>';
      } else {
        html += '<textarea type="text" id="input-'+question_index+'" name="#jspsych-survey-text-response-' + question_index + '" data-name="'+question.name+'" cols="' + question.columns + '" rows="' + question.rows + '" '+autofocus+' '+req+' placeholder="'+question.placeholder+'"></textarea>';
      }
      html += '</div>';
    }

    // add submit button
    html += '<input type="submit" id="jspsych-survey-text-next" class="jspsych-btn jspsych-survey-text" value="'+trial.button_label+'"></input>';

    html += '</form>'


    display_element.innerHTML = html;




        // backup in case autofocus doesn't work
        display_element.querySelector('#input-'+question_order[0]).focus();

        display_element.querySelector('#jspsych-survey-text-form').addEventListener('submit', function(e) {
          e.preventDefault();
          // measure response time
          var endTime = performance.now();
          var response_time = endTime - startTime;
    
          // create object to hold responses
          var question_data = {};
          
          for(var index=0; index < trial.questions.length; index++){
            var id = "Q" + index;
            var q_element = document.querySelector('#jspsych-survey-text-'+index).querySelector('textarea, input'); 
            var val = q_element.value;
            var name = q_element.attributes['data-name'].value;
            if(name == ''){
              name = id;
            }        
            var obje = {};
            obje[name] = val;
            Object.assign(question_data, obje);
          }
          // save data
          var trialdata = {
            "rt": response_time,
            "responses": JSON.stringify(question_data),
            "stimulus": trial.stimulus,
            "prompt": trial.correctAnswer
          };
    
          display_element.innerHTML = '';
    
          // next trial
          jsPsych.finishTrial(trialdata);
        });
    
        var startTime = performance.now();
      };
    }
      ImageTextResponseMASPlugin.info = info;

      return ImageTextResponseMASPlugin;
    })(jsPsychModule);
 

  
    
    /*
    // render
    display_element.innerHTML = html;

    // store response
    var response = {
      rt: null,
      //key: null
    };

    // function to end trial when it is time
    var end_trial = function() {

      // kill any remaining setTimeout handlers
      jsPsych.pluginAPI.clearAllTimeouts();

      // kill keyboard listeners
      if (typeof keyboardListener !== 'undefined') {
        jsPsych.pluginAPI.cancelKeyboardResponse(keyboardListener);
      }

      // gather the data to store for the trial
      var trial_data = {
        "rt": response.rt,
        "stimulus": trial.stimulus,
       // "key_press": response.key, 
        "prompt": trial.prompt
      };

      // clear the display
      display_element.innerHTML = '';

      // move on to the next trial
      jsPsych.finishTrial(trial_data);
    };

    // function to handle responses by the subject
    var after_response = function(info) {

      // after a valid response, the stimulus will have the CSS class 'responded'
      // which can be used to provide visual feedback that a response was recorded
      display_element.querySelector('#jspsych-image-keyboard-response-stimulus').className += ' responded';

      // only record the first response
      if (response.key == null) {
        response = info;
      }

      if (trial.response_ends_trial) {
        end_trial();
      }
    };

    // start the response listener
    if (trial.choices != jsPsych.NO_KEYS) {
      var keyboardListener = jsPsych.pluginAPI.getKeyboardResponse({
        callback_function: after_response,
        valid_responses: trial.choices,
        rt_method: 'performance',
        persist: false,
        allow_held_key: false
      });
    }

    // hide stimulus if stimulus_duration is set
    if (trial.stimulus_duration !== null) {
      jsPsych.pluginAPI.setTimeout(function() {
        display_element.querySelector('#jspsych-image-keyboard-response-stimulus').style.visibility = 'hidden';
      }, trial.stimulus_duration);
    }

    // end trial if trial_duration is set
    if (trial.trial_duration !== null) {
      jsPsych.pluginAPI.setTimeout(function() {
        end_trial();
      }, trial.trial_duration);
    }

  };

  return plugin;
})();*/
