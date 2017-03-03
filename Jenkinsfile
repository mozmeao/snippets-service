@Library('github.com/mozmar/jenkins-pipeline@20170303.1')
def stage_deployed = false
def config
def docker_image

conduit {
  node {
    stage("Prepare") {
      checkout scm
      setGitEnvironmentVariables()

      try {
        config = readYaml file: "jenkins.yml"
      }
      catch (e) {
        config = []
      }
      println "config ==> ${config}"

      if (!config || (config && config.pipeline && config.pipeline.enabled == false)) {
        println "Pipeline disabled."
      }
    }

    docker_image = "${config.project.docker_name}:${GIT_COMMIT_SHORT}"

    stage("Build") {
      if (!dockerImageExists(docker_image)) {
        sh "echo 'ENV GIT_SHA ${GIT_COMMIT}' >> Dockerfile"
        dockerImageBuild(docker_image, ["pull": true])
      }
      else {
        echo "Image ${docker_image} already exists."
      }
    }

    stage("Test") {
      parallel "Lint": {
        dockerRun(docker_image, "flake8 snippets")
      },
      "Unit Test": {
        def db_name = "mariadb-${env.GIT_COMMIT_SHORT}-${BUILD_NUMBER}"
        def args = [
          "docker_args": ("--name ${db_name} " +
                          "-e MYSQL_ALLOW_EMPTY_PASSWORD=yes " +
                          "-e MYSQL_DATABASE=snippets"),
        ]

        dockerRun("mariadb:10.0", args) {
          args = [
            "docker_args": ("--link ${db_name}:db " +
                            "-e CHECK_PORT=3306 " +
                            "-e CHECK_HOST=db")
          ]
          // Takis waits for mysql to come online
          dockerRun("giorgos/takis", args)

          args = [
            "docker_args": ("--link ${db_name}:db " +
                            "-e 'DEBUG=False' " +
                            "-e 'ALLOWED_HOSTS=*' " +
                            "-e 'SECRET_KEY=foo' " +
                            "-e 'DATABASE_URL=mysql://root@db/snippets' " +
                            "-e 'SITE_URL=http://localhost:8000' " +
                            "-e 'CACHE_URL=dummy://' " +
                            "-e 'SECURE_SSL_REDIRECT=False'"),
            "cmd": "coverage run ./manage.py test"
          ]
          dockerRun(docker_image, args)
        }
      }
    }

    stage("Upload Images") {
      dockerImagePush(docker_image, "mozjenkins-docker-hub")
    }
  }

  milestone()

  def deployStage = false
  def deployProd = false

  node {
    onBranch("master") {
      deployStage = true
    }
    onTag(/\d{4}\d{2}\d{2}.\d{1,2}/) {
      deployProd = true
    }
  }

  if (deployStage) {
    for (deploy in config.deploy.stage) {
      node {
        stage ("Deploying to ${deploy.name}") {
          lock("push to ${deploy.name}") {
            deisLogin(deploy.url, deploy.credentials) {
              deisPull(deploy.app, docker_image)
            }
            newRelicDeployment(deploy.newrelic_app, env.GIT_COMMIT_SHORT,
                               "jenkins", "newrelic-api-key")
          }
        }
      }
    }
  }
  if (deployProd) {
    for (deploy in config.deploy.prod) {
      timeout(time: 10, unit: 'MINUTES') {
        input("Push to ${deploy.name}?")
      }
      node {
        stage ("Deploying to ${deploy.name}") {
          lock("push to ${deploy.name}") {
            deisLogin(deploy.url, deploy.credentials) {
              deisPull(deploy.app, docker_image)
            }
            newRelicDeployment(deploy.newrelic_app, env.GIT_COMMIT_SHORT,
                               "jenkins", "newrelic-api-key")
          }
        }
      }
    }
  }
}
